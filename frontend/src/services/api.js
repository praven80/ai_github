import { Auth } from 'aws-amplify';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'https://api.aigithub.com';

/**
 * Get authentication headers
 */
async function getAuthHeaders() {
  try {
    const session = await Auth.currentSession();
    const token = session.getIdToken().getJwtToken();
    console.log("Got auth token (first 10 chars):", token.substring(0, 10));
    return {
      'Authorization': `Bearer ${token}`
    };
  } catch (error) {
    console.log('Not authenticated or session expired:', error);
    return {};
  }
}

/**
 * Fetch repository information
 */
export async function fetchRepoInfo(repoPath) {
  try {
    const authHeaders = await getAuthHeaders();
    console.log('Fetching repo info for:', repoPath);
    
    const response = await fetch(`${API_ENDPOINT}/api/repo-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ repoPath }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Repo info error response:', response.status, errorText);
      throw new Error(`Failed to fetch repo info: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API error in fetchRepoInfo:', error);
    throw error;
  }
}

/**
 * Send user message and get response about a repository
 */
export async function fetchRepoConversation(repoPath, message, conversationId = null) {
  try {
    const authHeaders = await getAuthHeaders();
    console.log('Sending chat message for repo:', repoPath);
    
    const requestBody = { 
      repoPath,
      message
    };
    
    // Include conversationId if provided
    if (conversationId) {
      requestBody.conversationId = conversationId;
    }
    
    const apiUrl = API_ENDPOINT + '/api/chat';
    console.log('Request details:', {
      url: apiUrl,
      body: requestBody
    });
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify(requestBody),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Chat API error response:', response.status, errorText);
      throw new Error("Failed to fetch conversation: Status " + response.status);
    }
    
    return await response.json();
    
  } catch (error) {
    console.error('API error in fetchRepoConversation:', error);
    throw error;
  }
}

/**
 * Fetch conversation history
 */
export async function fetchConversationHistory() {
  try {
    console.log("Fetching conversation history...");
    const authHeaders = await getAuthHeaders();
    
    if (!Object.keys(authHeaders).length) {
      console.log("No auth headers available, can't fetch history");
      return [];
    }
    
    // Manual test: log conversation history endpoint
    const url = `\${API_ENDPOINT}/api/conversation-history`;
    console.log("Making GET request to:", url);
    
    try {
      // Add timeout to avoid long waiting
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);
      
      // Make the request
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders
        },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      // Check response
      console.log("Conversation history API response status:", response.status);
      
      if (!response.ok) {
        throw new Error(`Server returned \${response.status}`);
      }
      
      // Get response text and try to parse
      const responseText = await response.text();
      console.log("Response text length:", responseText.length);
      
      // Parse JSON
      const data = JSON.parse(responseText);
      console.log("Retrieved conversation history:", data.length, "items");
      return data;
    } catch (error) {
      console.error("Error fetching conversation history:", error);
      
      // FALLBACK: Try direct scan for data - DEVELOPMENT ONLY
      try {
        console.log("Attempting direct DynamoDB access via /api/direct-scan");
        const scanResponse = await fetch(`\${API_ENDPOINT}/api/direct-scan`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders
          },
          body: JSON.stringify({ userId: "pvsaws@amazon.com" })
        });
        
        if (scanResponse.ok) {
          const scanData = await scanResponse.json();
          console.log("Retrieved data via scan:", scanData);
          return scanData;
        }
      } catch (scanError) {
        console.error("Failed scan attempt:", scanError);
      }
      
      // Return empty array if all attempts fail
      return [];
    }
  } catch (error) {
    console.error('API error in fetchConversationHistory:', error);
    return [];
  }
}

/**
 * Save conversation
 */
export async function saveConversation(conversationData) {
  try {
    console.group("SAVE CONVERSATION API CALL");
    console.log("API endpoint:", API_ENDPOINT);
    console.log("Data:", {
      id: conversationData.conversationId,
      repo: conversationData.repoPath,
      messageCount: conversationData.messages?.length
    });
    
    const authHeaders = await getAuthHeaders();
    console.log("Auth headers present:", Object.keys(authHeaders).length > 0);
    
    if (!Object.keys(authHeaders).length) {
      console.warn("No auth headers available for saving conversation");
      console.groupEnd();
      throw new Error("Authentication required to save conversations");
    }
    
    const fullUrl = `${API_ENDPOINT}/api/save-conversation`;
    console.log(`Sending POST request to: ${fullUrl}`);
    
    const response = await fetch(fullUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify(conversationData),
    });
    
    console.log("Save conversation API response status:", response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error("Save conversation error response:", errorText);
      console.groupEnd();
      throw new Error(`Failed to save conversation: ${response.status}`);
    }
    
    const data = await response.json();
    console.log("Save conversation response:", data);
    console.groupEnd();
    return data;
  } catch (error) {
    console.error('API error in saveConversation:', error);
    console.groupEnd();
    throw error;
  }
}

/**
 * Get specific conversation
 */
export async function getConversation(conversationId) {
  try {
    const authHeaders = await getAuthHeaders();
    
    const response = await fetch(`${API_ENDPOINT}/api/get-conversation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ conversationId }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get conversation: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API error:', error);
    throw error;
  }
}