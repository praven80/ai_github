# AI GitHub - Chat with GitHub Repositories

![AI GitHub Demo](demo/AIGitHub.gif)

A full-stack web application that allows users to have natural language conversations about any GitHub repository using AI. The application analyzes repository structure, code, documentation, issues, and other metadata to provide intelligent responses about the codebase.

## 🚀 Features

- **Natural Language Repository Analysis**: Ask questions about any public GitHub repository in plain English
- **Comprehensive Code Understanding**: Analyzes file structure, code content, README files, issues, pull requests, and more
- **User Authentication**: Secure sign-up/sign-in with AWS Cognito
- **Conversation History**: Save and retrieve past conversations (for authenticated users)
- **Real-time Chat Interface**: Interactive chat experience with markdown support
- **Repository Information Panel**: Display key repository stats and information
- **Responsive Design**: Works on desktop and mobile devices

## 🏗️ Architecture

### Backend (AWS Lambda + Python)
- **AWS Lambda**: Serverless function handling API requests
- **AWS Bedrock**: Claude 3.5 Haiku for AI-powered responses  
- **GitHub API**: Fetches repository data and metadata
- **DynamoDB**: Stores conversation history
- **AWS Secrets Manager**: Securely stores API keys
- **AWS Cognito**: User authentication and authorization

### Frontend (React)
- **React 18**: Modern React with hooks and context
- **AWS Amplify**: Cognito integration for authentication
- **Custom Components**: Chat interface, authentication forms, repository info
- **Markdown Support**: Custom markdown renderer for AI responses
- **Responsive CSS**: Mobile-friendly design

### Infrastructure (AWS)
- **API Gateway**: RESTful API endpoints
- **CloudFront**: CDN for fast global content delivery
- **S3**: Static website hosting
- **CloudFormation**: Infrastructure as Code

## 📋 Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Node.js 16+ and npm
- Python 3.9+
- GitHub Personal Access Token (optional, for higher API limits)

## 🛠️ Installation & Deployment

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ai-github
```

### 2. Configure GitHub Token (Optional)
Edit `infrastructure/deploy.sh` and add your GitHub token:
```bash
GITHUB_TOKEN="your_github_token_here"
```

### 3. Deploy to AWS
```bash
cd infrastructure
chmod +x deploy.sh
./deploy.sh
```

The deployment script will:
- Create necessary AWS resources using CloudFormation
- Build and deploy the Lambda function
- Build and deploy the React frontend
- Configure all AWS services and permissions

### 4. Access Your Application
After deployment, you'll receive:
- **Frontend URL**: Your CloudFront distribution URL
- **API Endpoint**: Your API Gateway endpoint URL

## 🔧 Local Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN="your_token"
export AWS_REGION="us-east-1"

# Test locally (requires AWS credentials configured)
python lambda_function.py
```

### Frontend Development  
```bash
cd frontend
npm install

# Create .env file with your API endpoint
echo "REACT_APP_API_ENDPOINT=https://your-api-url" > .env
echo "REACT_APP_AWS_REGION=us-east-1" >> .env
echo "REACT_APP_USER_POOL_ID=your_user_pool_id" >> .env
echo "REACT_APP_USER_POOL_CLIENT_ID=your_client_id" >> .env

npm start
```

## 💬 Usage

### 1. Access the Application
Visit your CloudFront URL or use the local development server.

### 2. Enter a Repository
On the home page, enter a GitHub repository in one of these formats:
- `owner/repository-name`
- `https://github.com/owner/repository-name`

### 3. Start Chatting
Ask questions about the repository:
- "What does this project do?"
- "How do I install and run this application?"
- "What are the main components of this codebase?"
- "Are there any open issues I should know about?"
- "What programming languages are used?"

### 4. Authentication (Optional)
Sign up or sign in to:
- Save conversation history
- Access conversations across devices
- Get personalized experience

## 🔑 Environment Variables

### Frontend (.env)
```
REACT_APP_API_ENDPOINT=https://your-api-gateway-url
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=us-east-1_xxxxxxxxx
REACT_APP_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
REACT_APP_IDENTITY_POOL_ID=us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Backend (Lambda Environment)
Set automatically by CloudFormation:
- `SECRETS_NAME`: AWS Secrets Manager secret name
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID

## 🗂️ Project Structure

```
ai_github/
├── backend/                    # Python Lambda function
│   ├── lambda_function.py     # Main Lambda handler
│   └── requirements.txt       # Python dependencies
├── frontend/                   # React application
│   ├── public/                # Static assets
│   ├── src/                   # React source code
│   │   ├── components/        # React components
│   │   ├── contexts/          # React contexts
│   │   ├── pages/             # Page components
│   │   └── services/          # API services
│   └── package.json           # Node.js dependencies
└── infrastructure/             # AWS infrastructure
    ├── cloudformation.yml     # CloudFormation template
    └── deploy.sh              # Deployment script
```

## 🛡️ Security Features

- **AWS Cognito Authentication**: Secure user management
- **CORS Configuration**: Proper cross-origin resource sharing
- **IAM Roles**: Least-privilege access principles
- **Secrets Management**: API keys stored securely in AWS Secrets Manager
- **JWT Token Validation**: Secure API access

## 🚀 Advanced Features

### Repository Analysis
The application analyzes:
- **File Structure**: Complete directory tree
- **Code Content**: Important files (README, config files, source code)
- **Repository Metadata**: Stars, forks, issues, contributors
- **Recent Activity**: Issues, pull requests, releases
- **Programming Languages**: Language distribution
- **Documentation**: README and other documentation files

### AI Capabilities
- **Contextual Understanding**: Maintains conversation context
- **Code Analysis**: Understands code structure and purpose
- **Multi-language Support**: Works with repositories in any programming language
- **Intelligent Responses**: Provides detailed, accurate information about repositories

## 🔧 Customization

### Adding New AI Models
To use different AI models, modify the `modelId` in `lambda_function.py`:
```python
response = bedrock_runtime.invoke_model(
    modelId="us.anthropic.claude-3-5-haiku-20241022-v1:0",  # Change this
    body=json.dumps(request_body),
    contentType="application/json"
)
```

### Extending API Endpoints
Add new endpoints by:
1. Adding resources in `cloudformation.yml`
2. Implementing handlers in `lambda_function.py`
3. Adding API calls in `frontend/src/services/api.js`

## 🐛 Troubleshooting

### Common Issues

**Lambda Timeout**: Increase timeout in CloudFormation template
```yaml
Timeout: 60  # Increase this value
```

**API Gateway CORS**: Ensure all endpoints have proper CORS configuration

**Authentication Issues**: Check Cognito configuration and JWT token handling

**GitHub API Rate Limits**: Add a GitHub token to increase limits

### Debugging
Check CloudWatch logs for Lambda function errors:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/aigithub"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- AWS Bedrock for AI capabilities
- GitHub API for repository data
- React community for excellent documentation
- AWS documentation and examples

## 📞 Support

For issues and questions:
1. Check the [troubleshooting section](#-troubleshooting)
2. Review CloudWatch logs
3. Open an issue in this repository

---

**Built with ❤️ using AWS, React, and AI**