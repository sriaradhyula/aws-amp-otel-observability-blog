import requests
import os

# Define variables for sensitive information
user_pool_domain = os.getenv('USER_POOL_DOMAIN')
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
scope = os.getenv('SCOPE')

# Define the token endpoint and payload
token_url = f'https://{user_pool_domain}/oauth2/token'
payload = {
  'grant_type': 'client_credentials',
  'client_id': client_id,
  'client_secret': client_secret,
  'scope': scope
}

# Define the headers
headers = {'Content-Type': 'application/x-www-form-urlencoded'}

# Print the token URL, payload, and headers
print("Token URL:", token_url)
print("Payload:", payload)
print("Headers:", headers)
# Make the POST request
response = requests.post(token_url, data=payload, headers=headers)

# Print the response JSON
print(response.json())