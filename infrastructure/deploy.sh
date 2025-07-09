#!/bin/bash

# Exit on error
set -e

# Configuration
STACK_NAME="aigithub-stack"
REGION="us-east-1" 
GITHUB_TOKEN=""  # Replace with your GitHub token

# Print configuration
echo "Using configuration:"
echo "STACK_NAME: $STACK_NAME"
echo "REGION: $REGION"

# Check if GitHub token is set
if [ -z "$GITHUB_TOKEN" ]; then
  echo "WARNING: GitHub token is not set. Please add your token to the script."
  echo "You can generate one at: https://github.com/settings/tokens"
  read -p "Do you want to continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Create deployment bucket with timestamp for uniqueness
TIMESTAMP=`date +%s`
DEPLOYMENT_BUCKET="aigithub-deployment-$TIMESTAMP"
echo "Creating deployment bucket: $DEPLOYMENT_BUCKET"

# Create deployment bucket
aws s3 mb "s3://$DEPLOYMENT_BUCKET" --region "$REGION"

# Install backend dependencies
echo "Installing backend dependencies..."
mkdir -p ./lambda-layer/python
pip install -r ./backend/requirements.txt -t ./lambda-layer/python
pip install python-jose pytz -t ./lambda-layer/python

# Create the Lambda layer
echo "Creating Lambda layer..."
cd ./lambda-layer
zip -r ../dependencies-layer.zip .
cd ..

# Upload Lambda layer to S3
echo "Uploading Lambda layer to S3..."
aws s3 cp dependencies-layer.zip "s3://$DEPLOYMENT_BUCKET/dependencies-layer.zip"

# Create a deployment package for the Lambda function
echo "Creating Lambda deployment package..."
cd ./backend
zip -r ../lambda-function.zip .
cd ..

# Upload Lambda function to S3
echo "Uploading Lambda function to S3..."
aws s3 cp lambda-function.zip "s3://$DEPLOYMENT_BUCKET/lambda-function.zip"

echo "Verifying files in S3 bucket..."
aws s3 ls "s3://$DEPLOYMENT_BUCKET/lambda-function.zip"
aws s3 ls "s3://$DEPLOYMENT_BUCKET/dependencies-layer.zip"

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file ./infrastructure/cloudformation.yml \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_IAM \
  --region "$REGION" \
  --parameter-overrides "DeploymentBucketName=$DEPLOYMENT_BUCKET"

# Get stack outputs
FRONTEND_BUCKET=$(aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --logical-resource-id FrontendBucket \
  --query "StackResources[0].PhysicalResourceId" \
  --output text \
  --region "$REGION")

API_ENDPOINT=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='APIEndpoint'].OutputValue" --output text --region "$REGION")
FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='FrontendURL'].OutputValue" --output text --region "$REGION")

# Get CloudFront distribution ID directly
DISTRIBUTION_ID=$(aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --logical-resource-id CloudFrontDistribution \
  --query "StackResources[0].PhysicalResourceId" \
  --output text \
  --region "$REGION")

# Get Cognito information
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text --region "$REGION")
USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" --output text --region "$REGION")
IDENTITY_POOL_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='IdentityPoolId'].OutputValue" --output text --region "$REGION")

echo "Stack deployed successfully!"
echo "Frontend Bucket: $FRONTEND_BUCKET"
echo "Frontend URL: $FRONTEND_URL"
echo "API Endpoint: $API_ENDPOINT"
echo "CloudFront Distribution ID: $DISTRIBUTION_ID"
echo "Cognito User Pool ID: $USER_POOL_ID"
echo "Cognito User Pool Client ID: $USER_POOL_CLIENT_ID"
echo "Cognito Identity Pool ID: $IDENTITY_POOL_ID"

# Update the secrets in Secrets Manager
echo "Updating API keys in Secrets Manager..."
aws secretsmanager update-secret \
  --secret-id AIGithubSecrets \
  --secret-string "{\"GITHUB_TOKEN\":\"$GITHUB_TOKEN\"}" \
  --region "$REGION"

# Check if we have a bucket name
if [ -z "$FRONTEND_BUCKET" ]; then
  echo "Frontend bucket name is empty!"
  echo "Getting bucket name directly from resources..."
  FRONTEND_BUCKET=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --logical-resource-id FrontendBucket \
    --query "StackResources[0].PhysicalResourceId" \
    --output text \
    --region "$REGION")
  echo "Found bucket: $FRONTEND_BUCKET"
fi

# Check again if we have a bucket name
if [ -z "$FRONTEND_BUCKET" ]; then
  echo "ERROR: Could not determine frontend bucket name. Upload manually."
  exit 1
fi

# Build frontend with AWS Amplify dependencies
echo "Building frontend..."
cd ./frontend

# Update package.json to include AWS Amplify
echo 'Adding AWS Amplify dependencies to package.json'
# Using node to update package.json programmatically
node -e '
const fs = require("fs");
const packageJson = JSON.parse(fs.readFileSync("./package.json", "utf8"));
packageJson.dependencies = packageJson.dependencies || {};
packageJson.dependencies["aws-amplify"] = "^5.3.12";
packageJson.dependencies["@aws-amplify/ui-react"] = "^5.3.2";
fs.writeFileSync("./package.json", JSON.stringify(packageJson, null, 2));
'

# Create .env file with API endpoint and Cognito config
echo "REACT_APP_API_ENDPOINT=$API_ENDPOINT" > .env
echo "REACT_APP_AWS_REGION=$REGION" >> .env
echo "REACT_APP_USER_POOL_ID=$USER_POOL_ID" >> .env
echo "REACT_APP_USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID" >> .env
echo "REACT_APP_IDENTITY_POOL_ID=$IDENTITY_POOL_ID" >> .env

# Install dependencies and build
npm install
npm run build
cd ..

# Upload frontend to S3
echo "Uploading frontend to S3..."
aws s3 sync ./frontend/build/ "s3://$FRONTEND_BUCKET" --delete

# Create CloudFront invalidation if we have a distribution ID
if [ ! -z "$DISTRIBUTION_ID" ]; then
  echo "Creating CloudFront invalidation..."
  aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"
else
  echo "Warning: Could not determine CloudFront distribution ID. Skipping invalidation."
fi

echo "==================================================="
echo "Deployment complete!"
echo "Frontend URL: $FRONTEND_URL"
echo "API URL: $API_ENDPOINT"
echo "==================================================="
echo "Cognito User Pool ID: $USER_POOL_ID"
echo "Cognito User Pool Client ID: $USER_POOL_CLIENT_ID"
echo "Cognito Identity Pool ID: $IDENTITY_POOL_ID"
echo "==================================================="
echo "You can now sign up and sign in to use the application"
echo "==================================================="