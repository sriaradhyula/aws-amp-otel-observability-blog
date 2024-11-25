# Create Cognito User Pool

- Create Cognito User Pool

```
aws cognito-idp create-user-pool --pool-name amp-testing --region us-east-2
```

- Create App Client for Cognito User Pool

```
aws cognito-idp create-user-pool-client --user-pool-id <Cognito User Pool ID from previous step> --region us-east-2  --client-name amp-testing --generate-secret --explicit-auth-flows "ALLOW_USER_AUTH" "ALLOW_USER_SRP_AUTH" "ALLOW_REFRESH_TOKEN_AUTH"
```

- Retrieve CLIENT_ID and CLIENT_SECRET from the previous command output.
