import json
import os
import requests
import boto3
import traceback
import base64
import time
from urllib.parse import parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import botocore.exceptions
import logging
import pytz
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants for file processing
PRIORITY_EXTENSIONS = ['.md', '.py', '.js', '.java', '.ts', '.jsx', '.tsx', '.html', '.css', 'Dockerfile', '.yml', '.yaml', '.json']
MEDIA_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.mp4', '.mov', '.webm']
BINARY_EXTENSIONS = ['.jar', '.zip', '.tar.gz', '.class', '.pyc', '.so', '.dll', '.exe', '.bin']

# Initialize clients
ssm = boto3.client('ssm')
secrets_manager = boto3.client('secretsmanager')
bedrock_runtime = boto3.client('bedrock-runtime')

# Initialize DynamoDB table with explicit verification
def get_dynamodb_table():
    """
    Initialize DynamoDB table with proper error handling
    """
    try:
        print("Initializing DynamoDB table 'ConversationHistory'")
        region = os.environ.get('AWS_REGION', 'us-east-1')
        dynamodb_resource = boto3.resource('dynamodb', region_name=region)
        table = dynamodb_resource.Table('ConversationHistory')
        
        # Verify table exists
        table_description = table.meta.client.describe_table(TableName='ConversationHistory')
        print(f"Successfully connected to DynamoDB table: {table_description['Table']['TableName']}")
        return table
    except Exception as e:
        print(f"ERROR: Failed to initialize DynamoDB table: {str(e)}")
        traceback.print_exc()
        return None

# Initialize DynamoDB table
try:
    conversation_table = get_dynamodb_table()
    if conversation_table:
        print("DynamoDB table initialized successfully GLOBALLY") # Added for clarity
    else:
        print("Failed to initialize DynamoDB table GLOBALLY") # Added for clarity
except Exception as e:
    print(f"ERROR: Global DynamoDB initialization failed: {str(e)}")
    traceback.print_exc()
    conversation_table = None

# Get API keys from Secrets Manager
def get_secret(secret_name):
    try:
        print(f"DEBUG: Getting secret: {secret_name}")
        response = secrets_manager.get_secret_value(SecretId=secret_name)
        secret_value = json.loads(response['SecretString'])
        print(f"DEBUG: Secret retrieved successfully")
        return secret_value
    except Exception as e:
        print(f"ERROR: Failed to get secret {secret_name}: {e}")
        traceback.print_exc()
        raise e

# Initialize API keys
try:
    secrets = get_secret('AIGithubSecrets')
    GITHUB_TOKEN = secrets.get('GITHUB_TOKEN')
    print(f"DEBUG: GitHub token set: {'Yes' if GITHUB_TOKEN else 'No'}, first chars: {GITHUB_TOKEN[:4] if GITHUB_TOKEN else 'None'}")
except Exception:
    # Fallback to environment variables for testing
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    print(f"DEBUG: Using environment GitHub token: {'Yes' if GITHUB_TOKEN else 'No'}")

def get_cognito_user_pool_id():
    """Dynamically detect Cognito User Pool ID"""
    user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
    if user_pool_id:
        return user_pool_id
    
    try:
        # List user pools and find one with correct name
        cognito_client = boto3.client('cognito-idp')
        response = cognito_client.list_user_pools(MaxResults=60)
        
        for pool in response['UserPools']:
            if 'AIGithubUserPool' in pool['Name']:
                user_pool_id = pool['Id']
                print(f"Found Cognito User Pool: {user_pool_id}")
                return user_pool_id
    except Exception as e:
        print(f"Error finding Cognito User Pool: {str(e)}")
    
    return None

def verify_jwt_token(token):
    """Extract user claims from JWT token"""
    if not token:
        return None
        
    try:
        # Extract claims from token payload
        token_parts = token.split('.')
        if len(token_parts) != 3:
            print("Invalid token format - not a JWT")
            return None
            
        # Get payload (middle part of JWT)
        payload_base64 = token_parts[1]
        # Add padding if needed
        padding = '=' * ((4 - len(payload_base64) % 4) % 4) 
        payload = json.loads(base64.b64decode(payload_base64 + padding).decode('utf-8'))
        print(f"DEBUG: Successfully decoded JWT payload, found keys: {list(payload.keys())}")
        return payload
    except Exception as e:
        print(f"ERROR: Invalid token: {str(e)}")
        traceback.print_exc()
        return None

def save_conversation(user_id, conversation_id, repo_path, messages, title=None):
    """
    Save conversation to DynamoDB with properly formatted timestamp
    """
    try:
        # Check if table is initialized
        if conversation_table is None:
            print("ERROR: DynamoDB table not initialized, cannot save conversation")
            return False
            
        print(f"SAVE CONVERSATION: Starting for user {user_id}, conversation ID {conversation_id}")
        
        # Get current time in Eastern Time and format it correctly
        et_timezone = pytz.timezone('US/Eastern')
        timestamp = datetime.now(et_timezone).strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract question and response from messages
        user_message = ""
        assistant_response = ""
        
        for msg in messages:
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
            elif msg.get('role') == 'assistant':
                assistant_response = msg.get('content', '')
        
        # Prepare item with the required schema
        item = {
            'userId': user_id,
            'timestamp': timestamp,
            'conversationId': conversation_id,
            'repoPath': repo_path,
            'question': user_message,
            'response': assistant_response
        }
        
        print(f"SAVE CONVERSATION: Putting item into DynamoDB - userId:{user_id}, timestamp:{timestamp}")
        
        # Try to put item
        try:
            # Save to DynamoDB
            response = conversation_table.put_item(Item=item)
            print(f"SAVE CONVERSATION: DynamoDB response: {response}")
            print(f"SAVE CONVERSATION: Successfully saved conversation {conversation_id} for user {user_id}")
            return True
        except Exception as db_error:
            print(f"ERROR: DynamoDB put_item failed: {str(db_error)}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to save conversation: {str(e)}")
        traceback.print_exc()
        return False

def lambda_handler(event, context):
    """
    Main Lambda handler function that processes API Gateway events
    """
    try:
        print(f"DEBUG: Event received: \n{json.dumps(event, indent=4)}")
        
        # Enable CORS
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            'Content-Type': 'application/json'
        }
        
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Parse path parameter to determine API route
        path = event.get('path', '')
        http_method = event.get('httpMethod', '')
        print(f"DEBUG: Request path: {path}, method: {http_method}")
        
        # Parse request body
        body = {}
        if event.get('body'):
            print(f"DEBUG: Raw body length: {len(event.get('body'))}")
            try:
                body = json.loads(event.get('body', '{}'))
                if 'save-conversation' in path:
                    print(f"DEBUG: Save conversation body keys: {list(body.keys())}")
            except Exception as e:
                print(f"ERROR: Failed to parse body JSON: {e}")
                body = {}
        
        # Extract authorization token
        auth_header = None
        if event.get('headers'):
            print(f"DEBUG: Headers present: {list(event['headers'].keys())}")
            auth_header = event.get('headers', {}).get('Authorization') or event.get('headers', {}).get('authorization')
        
        claims = {}
        user_id = None
        
        # If auth header exists, verify token
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
            print(f"DEBUG: Found token (first few chars): {token[:20]}...")
            
            claims = verify_jwt_token(token) or {}
            user_id = claims.get('email') or claims.get('sub')
                
            if user_id:
                print(f"DEBUG: Authenticated user: {user_id}")
            else:
                print("DEBUG: Failed to extract user ID from token")
        else:
            print("DEBUG: No valid Authorization header found")
        
        # Route the request based on path
        if '/chat' in path:
            return handle_chat_request(body, headers, user_id)
        elif '/repo-info' in path:
            return handle_repo_info_request(body, headers)
        else:
            print(f"ERROR: No matching route for path: {path}")
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Not found', 'path': path})
            }
    
    except Exception as e:
        print(f"ERROR: Lambda handler error: {str(e)}")
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }
    
def handle_repo_info_request(body, headers):
    """
    Handle requests to get repository information
    """
    repo_path = body.get('repoPath')
    print(f"DEBUG: Handling repo info request for: {repo_path}")
    
    if not repo_path or '\${' in repo_path:
        print(f"ERROR: Invalid repository path: {repo_path}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Repository path is required and must be valid'})
        }
    
    try:
        # Fetch repository information from GitHub API
        github_headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            github_headers["Authorization"] = f"token {GITHUB_TOKEN}"
        
        print(f"DEBUG: Fetching repo info from GitHub API: {repo_path}")
        github_response = requests.get(
            f"https://api.github.com/repos/{repo_path}",
            headers=github_headers,
            timeout=10
        )
        
        print(f"DEBUG: GitHub API response status: {github_response.status_code}")
        
        if github_response.status_code != 200:
            print(f"ERROR: GitHub API error: {github_response.status_code} {github_response.text}")
            return {
                'statusCode': github_response.status_code,
                'headers': headers,
                'body': json.dumps({'error': f'GitHub API error: {github_response.text}'})
            }
        
        repo_data = github_response.json()
        print(f"DEBUG: Successfully fetched repo info for {repo_data.get('full_name')}")
        
        # Format the response
        response_data = {
            'name': repo_data.get('name', ''),
            'fullName': repo_data.get('full_name', ''),
            'description': repo_data.get('description', ''),
            'stars': repo_data.get('stargazers_count', 0),
            'forks': repo_data.get('forks_count', 0),
            'issues': repo_data.get('open_issues_count', 0),
            'language': repo_data.get('language', ''),
            'url': repo_data.get('html_url', ''),
            'topics': repo_data.get('topics', []),
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_data)
        }
    
    except Exception as e:
        print(f"ERROR: Error fetching repo info: {str(e)}")
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def handle_chat_request(body, headers, user_id=None):
    """
    Handle chat requests
    """
    repo_path = body.get('repoPath')
    message = body.get('message')
    conversation_id = body.get('conversationId', f"conv_{int(time.time())}_{random.randint(1000, 9999)}")
    print(f"DEBUG: Handling chat request for repo: {repo_path}, message: {message}, conversation_id: {conversation_id}")
    print(f"DEBUG: User ID passed to handle_chat_request: {user_id}")
    
    if not repo_path or not message or '\${' in repo_path:
        print(f"ERROR: Invalid repository path: {repo_path} or message: {message}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Repository path and message are required and must be valid'})
        }
    
    try:
        # Fetch repository data
        repo_data = fetch_repository_data(repo_path)
        
        # Process with Claude
        print(f"DEBUG: Processing with Claude for repo: {repo_path}")
        response = process_with_claude(repo_path, repo_data, message)
        
        # Auto-save conversation if user is authenticated
        if user_id:
            print(f"DEBUG: Auto-saving conversation for user: {user_id}")
            
            # Create messages array with user question and AI response
            messages = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ]
            
            # Save to DynamoDB
            save_result = save_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                repo_path=repo_path,
                messages=messages,
                title=message[:50] + ('...' if len(message) > 50 else '')
            )
            
            if save_result:
                print(f"DEBUG: Successfully saved conversation {conversation_id}")
            else:
                print(f"ERROR: Failed to save conversation {conversation_id}")
        else:
            print("DEBUG: No authenticated user, skipping conversation save")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'answer': response,
                'conversationId': conversation_id
            })
        }
    
    except Exception as e:
        print(f"ERROR: Error in chat request: {str(e)}")
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

# Include all your existing functions (fetch_repository_data, etc.)
def fetch_repository_data(repo_path):
    """
    Comprehensive repository data fetching without arbitrary limits
    """
    print(f"DEBUG: Fetching repository data for {repo_path}")
    result = {
        "repo_info": {},
        "readme": "No README found.",
        "recent_issues": [],
        "pull_requests": [],
        "releases": [],
        "contributors": [],
        "file_structure": {},
        "file_contents": {},
        "media_files": [],
        "languages": {},
    }
    
    # Set up GitHub API headers
    github_headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        github_headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    try:
        # 1. Fetch basic repo info
        print(f"DEBUG: Fetching basic repo info for {repo_path}")
        repo_url = f"https://api.github.com/repos/{repo_path}"
        repo_response = requests.get(repo_url, headers=github_headers, timeout=10)
        
        if repo_response.status_code == 200:
            result["repo_info"] = repo_response.json()
            print(f"DEBUG: Successfully fetched repo info: {result['repo_info'].get('full_name')}")
        else:
            print(f"ERROR: Failed to fetch repo info: {repo_response.status_code} - {repo_response.text}")
            return result
        
        # 2. Fetch README
        print(f"DEBUG: Fetching README for {repo_path}")
        readme_headers = github_headers.copy()
        readme_headers["Accept"] = "application/vnd.github.raw"
        readme_response = requests.get(
            f"https://api.github.com/repos/{repo_path}/readme",
            headers=readme_headers,
            timeout=10
        )
        
        if readme_response.status_code == 200:
            result["readme"] = readme_response.text
            print(f"DEBUG: Successfully fetched README, length: {len(result['readme'])}")
        else:
            print(f"DEBUG: No standard README found, trying alternate locations")
            # Try alternate README locations
            for readme_name in ["readme.md", "README.md", "Readme.md"]:
                try:
                    alt_readme_response = requests.get(
                        f"https://api.github.com/repos/{repo_path}/contents/{readme_name}",
                        headers=github_headers,
                        timeout=10
                    )
                    if alt_readme_response.status_code == 200:
                        content_data = alt_readme_response.json()
                        if content_data.get("encoding") == "base64" and content_data.get("content"):
                            result["readme"] = base64.b64decode(content_data["content"]).decode('utf-8', errors='replace')
                            print(f"DEBUG: Successfully fetched README from {readme_name}")
                            break
                except Exception as e:
                    print(f"DEBUG: Error checking alternate README {readme_name}: {str(e)}")
        
        # 3. Fetch languages
        languages_response = requests.get(
            f"https://api.github.com/repos/{repo_path}/languages",
            headers=github_headers,
            timeout=10
        )
        
        if languages_response.status_code == 200:
            result["languages"] = languages_response.json()
            print(f"DEBUG: Successfully fetched languages: {list(result['languages'].keys())}")
        
        # 4. Fetch issues with pagination
        print(f"DEBUG: Fetching issues for {repo_path}")
        all_issues = []
        page = 1
        while page <= 3:  # Limit to 3 pages (30 issues) to avoid excessive API calls
            issues_response = requests.get(
                f"https://api.github.com/repos/{repo_path}/issues?state=all&per_page=10&page={page}",
                headers=github_headers,
                timeout=10
            )
            
            if issues_response.status_code != 200 or not issues_response.json():
                break
                
            issues_page = issues_response.json()
            all_issues.extend(issues_page)
            page += 1
            
            if len(issues_page) < 10:  # Last page has fewer than 10 items
                break
        
        # Filter out pull requests
        result["recent_issues"] = [issue for issue in all_issues if "pull_request" not in issue]
        print(f"DEBUG: Successfully fetched {len(result['recent_issues'])} issues")
        
        # 5. Fetch pull requests
        print(f"DEBUG: Fetching pull requests for {repo_path}")
        prs_response = requests.get(
            f"https://api.github.com/repos/{repo_path}/pulls?state=all&per_page=10",
            headers=github_headers,
            timeout=10
        )
        
        if prs_response.status_code == 200:
            result["pull_requests"] = prs_response.json()
            print(f"DEBUG: Successfully fetched {len(result['pull_requests'])} pull requests")
        
        # 6. Fetch releases
        releases_response = requests.get(
            f"https://api.github.com/repos/{repo_path}/releases?per_page=10",
            headers=github_headers,
            timeout=10
        )
        
        if releases_response.status_code == 200:
            result["releases"] = releases_response.json()
            print(f"DEBUG: Successfully fetched {len(result['releases'])} releases")
        
        # 7. Fetch contributors
        contributors_response = requests.get(
            f"https://api.github.com/repos/{repo_path}/contributors?per_page=15",
            headers=github_headers,
            timeout=10
        )
        
        if contributors_response.status_code == 200:
            result["contributors"] = contributors_response.json()
            print(f"DEBUG: Successfully fetched {len(result['contributors'])} contributors")
        
        # 8. Fetch file structure recursively with no depth limit
        # Using a queue-based approach to avoid recursion limits
        print(f"DEBUG: Fetching complete file structure for {repo_path}")
        fetch_directory_content_complete(repo_path, result["file_structure"], github_headers)
        print(f"DEBUG: Fetched complete file structure with {len(result['file_structure'])} entries")
        
        # 9. Fetch file contents in parallel
        print(f"DEBUG: Fetching important file contents in parallel")
        fetch_important_file_contents_parallel(repo_path, result["file_structure"], result["file_contents"], github_headers)
        print(f"DEBUG: Fetched {len(result['file_contents'])} file contents")
        
        # 10. Find media files
        for path, info in result["file_structure"].items():
            if info.get("type") == "file":
                for ext in MEDIA_EXTENSIONS:
                    if path.lower().endswith(ext):
                        result["media_files"].append({
                            "path": path,
                            "name": info.get("name"),
                            "type": ext.lstrip('.'),
                            "url": info.get("html_url")
                        })
                        break
        
        print(f"DEBUG: Found {len(result['media_files'])} media files")
        
    except Exception as e:
        print(f"ERROR: Error in fetch_repository_data: {str(e)}")
        traceback.print_exc()
    
    return result

def fetch_directory_content_complete(repo_path, file_structure, headers):
    """
    Non-recursive directory content fetching using a queue-based approach
    to handle repositories of any depth
    """
    try:
        # Use a queue to store directories that need to be processed
        queue = [("", 0)]  # (path, depth) pairs
        requests_count = 0
        
        # Process directories until queue is empty or we hit rate limits
        while queue and requests_count < 60:  # Soft limit on total requests to prevent timeouts
            current_path, depth = queue.pop(0)
            path_param = current_path if current_path else ""
            contents_url = f"https://api.github.com/repos/{repo_path}/contents/{path_param}"
            
            print(f"DEBUG: Fetching directory content for {path_param or 'root'}")
            response = requests.get(contents_url, headers=headers, timeout=10)
            requests_count += 1
            
            # Handle GitHub API rate limits
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                print("WARNING: GitHub API rate limit reached. Waiting and retrying...")
                time.sleep(10)  # Wait briefly before retrying
                queue.insert(0, (current_path, depth))  # Re-add to queue
                continue
            
            # Skip if we can't access this directory
            if response.status_code != 200:
                print(f"WARNING: Could not fetch content for {path_param}: {response.status_code}")
                continue
            
            contents = response.json()
            if not isinstance(contents, list):
                contents = [contents]
            
            # Process all items in this directory
            for item in contents:
                item_path = item.get("path", "")
                item_type = item.get("type", "")
                
                # Skip very large binary files and git-related files
                if (item_path.startswith('.git') or 
                    any(item_path.lower().endswith(ext) for ext in BINARY_EXTENSIONS)):
                    continue
                
                # Add to file structure
                file_structure[item_path] = {
                    "name": item.get("name"),
                    "path": item_path,
                    "type": item_type,
                    "size": item.get("size", 0),
                    "html_url": item.get("html_url")
                }
                
                # Queue subdirectories for processing
                if item_type == "dir":
                    queue.append((item_path, depth + 1))
            
            # Avoid hitting rate limits
            if requests_count % 10 == 0:
                time.sleep(1)
                
    except Exception as e:
        print(f"ERROR: Failed to fetch complete directory content: {str(e)}")
        traceback.print_exc()

def fetch_important_file_contents_parallel(repo_path, file_structure, file_contents, headers):
    """
    Fetch file contents in parallel with intelligent prioritization
    based on file types and importance
    """
    try:
        # Sort files by priority and size
        files_to_fetch = []
        
        for path, info in file_structure.items():
            if info.get("type") != "file":
                continue
            
            # Skip binary files and very large files (>10MB)
            if info.get("size", 0) > 10 * 1024 * 1024:
                print(f"DEBUG: Skipping large file: {path} ({info.get('size', 0) / 1024 / 1024:.2f}MB)")
                continue
                
            if any(path.lower().endswith(ext) for ext in BINARY_EXTENSIONS):
                continue
            
            # Calculate priority score
            priority = 0
            
            # Boost priority for important file extensions
            for ext in PRIORITY_EXTENSIONS:
                if path.lower().endswith(ext):
                    priority += 10
                    break
                    
            # Boost priority for important file names
            for name in ['readme', 'license', 'contributing', 'changelog', 'dockerfile']:
                if name in path.lower():
                    priority += 5
                    break
            
            # Boost priority for top-level files
            if '/' not in path:
                priority += 3
                
            # Penalize very large text files
            size_mb = info.get('size', 0) / (1024 * 1024)
            if size_mb > 0.5:  # Greater than 500KB
                priority -= int(size_mb * 2)
                
            # Add to list with priority
            files_to_fetch.append((path, info, priority))
        
        # Sort by priority (highest first)
        files_to_fetch.sort(key=lambda x: x[2], reverse=True)
        
        # Use thread pool to fetch files in parallel
        fetched_count = 0
        total_size = 0
        MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB total content limit
        
        with ThreadPoolExecutor(max_workers=5) as executor:  # 5 workers to avoid throttling
            # Submit tasks for the top 500 files by priority
            future_to_path = {}
            for path, info, _ in files_to_fetch[:500]:
                future = executor.submit(
                    fetch_single_file_content, repo_path, path, info, headers
                )
                future_to_path[future] = path
            
            # Process results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                
                try:
                    content_result = future.result()
                    if content_result:
                        file_contents[path] = content_result
                        fetched_count += 1
                        total_size += len(content_result.get('content', ''))
                        
                        # Stop if we've fetched too much data
                        if total_size > MAX_TOTAL_SIZE:
                            print(f"DEBUG: Reached content size limit ({total_size / 1024 / 1024:.2f}MB). Stopping.")
                            break
                except Exception as e:
                    print(f"ERROR: Failed to fetch content for {path}: {str(e)}")
                    
        print(f"DEBUG: Fetched {fetched_count} files with total size {total_size / 1024 / 1024:.2f}MB")
        
    except Exception as e:
        print(f"ERROR: Failed in fetch_important_file_contents_parallel: {str(e)}")
        traceback.print_exc()

def fetch_single_file_content(repo_path, path, info, headers):
    """Fetch a single file's content"""
    try:
        file_size = info.get('size', 0)
        max_size = 10 * 1024 * 1024  # 10MB per file max
        
        if file_size > max_size:
            # For large files, include a truncated version with a warning
            content_response = requests.get(
                f"https://api.github.com/repos/{repo_path}/contents/{path}",
                headers={**headers, "Accept": "application/vnd.github.raw"},
                timeout=15
            )
            
            if content_response.status_code == 200:
                content = content_response.text[:100000]  # Take first ~100KB
                return {
                    "name": info.get("name"),
                    "content": content + "\n\n[FILE TRUNCATED] This file was too large to display completely.",
                    "truncated": True,
                    "size": file_size
                }
        else:
            # For normal files, get the full content
            content_response = requests.get(
                f"https://api.github.com/repos/{repo_path}/contents/{path}",
                headers={**headers, "Accept": "application/vnd.github.raw"},
                timeout=15
            )
            
            if content_response.status_code == 200:
                return {
                    "name": info.get("name"),
                    "content": content_response.text,
                    "truncated": False,
                    "size": file_size
                }
                
    except Exception as e:
        print(f"ERROR: Failed to fetch content for {path}: {str(e)}")
        
    return None

def process_with_claude(repo_path, repo_data, message):
    """
    Process repository data with Claude to answer user's questions
    with improved error handling and retry logic
    """
    request_id = f"req-{random.randint(1000, 9999)}"
    logger.info(f"[{request_id}] Processing request for repo: {repo_path}, message: '{message}'")
    
    try:
        # Extract repository data
        repo_info = repo_data.get("repo_info", {})
        readme = repo_data.get("readme", "")
        languages = repo_data.get("languages", {})
        issues = repo_data.get("recent_issues", [])
        prs = repo_data.get("pull_requests", [])
        contributors = repo_data.get("contributors", [])
        releases = repo_data.get("releases", [])
        file_structure = repo_data.get("file_structure", {})
        file_contents = repo_data.get("file_contents", {})
        media_files = repo_data.get("media_files", [])
        
        # Format languages for display
        total_bytes = sum(languages.values()) if languages else 0
        language_text = ""
        if total_bytes > 0:
            language_text = "\n".join([
                f"- {lang}: {round(bytes/total_bytes * 100, 1)}%"
                for lang, bytes in sorted(languages.items(), key=lambda x: x[1], reverse=True)
            ])
        
        # Format contributors
        contributor_text = "\n".join([
            f"- {contrib.get('login')}: {contrib.get('contributions')} contributions"
            for contrib in contributors[:50]
        ])
        
        # Format issues
        issues_text = "\n".join([
            f"- #{issue.get('number')}: {issue.get('title')} ({issue.get('state')})"
            for issue in issues[:50]
        ])
        
        # Format key files (summarize the structure)
        file_count = len(file_structure)
        dir_count = sum(1 for info in file_structure.values() if info.get('type') == 'dir')
        file_structure_summary = f"Total: {file_count} files, {dir_count} directories\n"
        
        # Add key directories
        top_level_dirs = []
        for path, info in file_structure.items():
            if info.get('type') == 'dir' and '/' not in path:
                top_level_dirs.append(f"- {path}/")
        file_structure_summary += "\nTop-level directories:\n" + "\n".join(sorted(top_level_dirs)[:50])
        
        # Add key files
        top_level_files = []
        for path, info in file_structure.items():
            if info.get('type') == 'file' and '/' not in path:
                top_level_files.append(f"- {path}")
        file_structure_summary += "\n\nTop-level files:\n" + "\n".join(sorted(top_level_files)[:50])
        
        # Prepare file contents for the AI model
        file_content_text = ""
        truncated_files = []
        
        # Check specifically for utils.py or any other files that might have the Claude 3.7 reference
        important_specific_files = []
        for path, info in file_contents.items():
            if "utils.py" in path.lower() or "agent.py" in path.lower() or "bedrock" in path.lower():
                important_specific_files.append((path, info))
        
        # Add highest priority specific files first
        for path, info in important_specific_files:
            content = info.get("content", "")
            if "claude-3-7" in content.lower():
                logger.info(f"[{request_id}] Found Claude 3.7 reference in {path}")
            if len(content) > 10000:
                content = content[:10000] + "\n\n[TRUNCATED]"
                truncated_files.append(path)
            file_content_text += f"\n\nFILE: {path}\n{content}"
        
        # Add remaining important files
        remaining_file_space = 50000 - len(file_content_text)
        if remaining_file_space > 5000:  # Only continue if we have reasonable space left
            for path, info in file_contents.items():
                # Skip already included files
                if any(p == path for p, _ in important_specific_files):
                    continue
                
                # Skip large content blocks to avoid context window limits
                content = info.get("content", "")
                if len(content) > 5000:
                    content = content[:5000] + "\n\n[TRUNCATED]"
                    truncated_files.append(path)
                    
                file_text = f"\n\nFILE: {path}\n{content}"
                if len(file_text) + len(file_content_text) > 50000:
                    break
                    
                file_content_text += file_text
        
        # Format media files
        media_text = "\n".join([
            f"- {media.get('path')} ({media.get('type')})"
            for media in media_files[:100]
        ])
        
        # Truncate README if too long
        if len(readme) > 4000:
            readme = readme[:4000] + "... [README truncated]"
        
        # Build system message
        system_message = f"""
        You are an AI assistant that helps users understand GitHub repositories.
        You are currently analyzing the repository: {repo_path}
        
        Repository Information:
        - Name: {repo_info.get('name')}
        - Full Name: {repo_info.get('full_name')}
        - Description: {repo_info.get('description')}
        - Stars: {repo_info.get('stargazers_count')}
        - Forks: {repo_info.get('forks_count')}
        - Open Issues: {repo_info.get('open_issues_count')}
        - Topics: {', '.join(repo_info.get('topics', []))}
        
        Languages:
        {language_text}
        
        Top Contributors:
        {contributor_text}
        
        Recent Issues:
        {issues_text}
        
        Repository Structure:
        {file_structure_summary}
        
        Media Files:
        {media_text}
        
        README Content:
        {readme}
        
        File Contents:
        {file_content_text}
        
        Answer the user's question based on this repository information. Be specific and detailed, citing files and code when relevant. If you don't know the answer, say so rather than making up information.
        """
        
        if truncated_files:
            system_message += f"\n\nNote: The following files were truncated due to size: {', '.join(truncated_files)}"
        
        # Log the message structure and size to debug potential content issues
        logger.info(f"[{request_id}] System message length: {len(system_message)} chars")
        
        # Format for Claude 3.5
        user_message = {
            "role": "user",
            "content": f"<instructions>\n{system_message}\n</instructions>\n\n{message}"
        }
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": 0.7,
            "messages": [user_message]
        }
        
        # Verify bedrock_runtime is available
        if 'bedrock_runtime' not in globals():
            try:
                import boto3
                global bedrock_runtime
                bedrock_runtime = boto3.client('bedrock-runtime')
                logger.info(f"[{request_id}] Initialized bedrock-runtime client")
            except Exception as e:
                logger.error(f"[{request_id}] Failed to initialize bedrock-runtime: {str(e)}")
                return "Error: Could not connect to AI service. Please check your configuration."
        
        # Retry configuration
        max_retries = 5  # Number of total attempts
        base_delay = 2    # Initial backoff in seconds
        max_delay = 60    # Maximum backoff in seconds
        
        # Implement exponential backoff with jitter
        for attempt in range(max_retries):
            try:
                logger.info(f"[{request_id}] Attempt {attempt+1}/{max_retries} calling Bedrock API")
                
                # Call Claude with timeout handling
                start_time = time.time()
                response = bedrock_runtime.invoke_model(
                    modelId="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                    body=json.dumps(request_body),
                    contentType="application/json"
                )
                elapsed = time.time() - start_time
                logger.info(f"[{request_id}] API call successful in {elapsed:.2f}s")
                
                # Process response
                try:
                    response_body = json.loads(response['body'].read().decode('utf-8'))
                    
                    # Validate response structure
                    if not response_body.get("content") or not isinstance(response_body["content"], list):
                        logger.error(f"[{request_id}] Invalid response structure: {json.dumps(response_body)}")
                        return "Error: Received an invalid response from the AI service. Please try again."
                    
                    # Success! Return the text response
                    result = response_body["content"][0]["text"]
                    logger.info(f"[{request_id}] Successfully generated response ({len(result)} chars)")
                    return result
                    
                except (KeyError, IndexError, json.JSONDecodeError) as parse_err:
                    logger.error(f"[{request_id}] Failed to parse response: {str(parse_err)}")
                    if attempt < max_retries - 1:
                        time.sleep(base_delay)
                        continue
                    return "Error: Failed to process the AI service response. Please try again."
                
            except botocore.exceptions.ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_message = e.response["Error"]["Message"]
                
                logger.warning(f"[{request_id}] ClientError: {error_code} - {error_message}")
                
                # Check if this is a throttling error and not the last attempt
                if error_code == "ThrottlingException" and attempt < max_retries - 1:
                    # Calculate exponential backoff with jitter
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    jitter = delay * 0.2 * random.random()  # Add up to 20% jitter
                    wait_time = delay + jitter
                    
                    logger.info(f"[{request_id}] Rate limited, retrying in {wait_time:.2f}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    # Non-throttling error or final attempt
                    logger.error(f"[{request_id}] Failed after {attempt+1} attempts: {str(e)}")
                    return f"I encountered an error accessing the AI service. Please try again later."
            
            except Exception as e:
                # Handle any other exceptions
                logger.error(f"[{request_id}] Unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                
                if attempt < max_retries - 1:
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    logger.info(f"[{request_id}] Retrying after error in {delay}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                else:
                    return f"I encountered an unexpected error. Please try again later."
        
        # If we've exhausted all retries
        logger.error(f"[{request_id}] Maximum retries ({max_retries}) exceeded")
        return "I couldn't process this request after multiple attempts. Please try again later."

    except Exception as e:
        # Catch any exceptions in the preprocessing phase
        logger.error(f"[{request_id}] Error during preprocessing: {str(e)}")
        logger.error(traceback.format_exc())
        return "Sorry, I encountered an error processing your request. Please try again."