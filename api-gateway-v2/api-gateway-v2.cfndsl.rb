CloudFormation do

    Resource('Api') do
        Type('AWS::ApiGatewayV2::Api')
        Property('ProtocolType', 'HTTP')
        Property('Name', 'amis')
        Property('ApiKeySelectionExpression', '$request.header.x-api-key')
        Property('RouteSelectionExpression', '$request.method $request.path')
        Property('CorsConfiguration', {
            AllowCredentials: false,
            AllowMethods: [
                "GET"
            ],
            AllowOrigins: [
                "*"
            ],
            MaxAge: 0
        })
    end

    Resource('Deployment') do
        DependsOn('Route')
        Type('AWS::ApiGatewayV2::Deployment')
        Property('ApiId', Ref('Api'))
    end

    Resource('Stage') do
        Type('AWS::ApiGatewayV2::Stage')
        Property('AccessLogSettings', {
            DestinationArn: FnGetAtt("LogGroup", "Arn"),
            Format: '{"requestId":"$context.requestId", "ip": "$context.identity.sourceIp", "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod","routeKey":"$context.routeKey", "status":"$context.status","protocol":"$context.protocol", "responseLength":"$context.responseLength" }'
        })
        Property('ApiId', Ref('Api'))
        Property('AutoDeploy', true)
        Property('DefaultRouteSettings', {
            DetailedMetricsEnabled: false
        })
        Property('DeploymentId', Ref('Deployment'))
        Property('RouteSettings', {})
        Property('StageName', '$default')
        Property('StageVariables', {})
        Property('Tags', {})
    end

    Resource('Integration') do
        Type('AWS::ApiGatewayV2::Integration')
        Property('ApiId', Ref('Api'))
        Property('ConnectionType', 'INTERNET')
        Property('IntegrationType', 'AWS_PROXY')
        Property('IntegrationUri', Ref('GetAmiFunctionArn'))
        Property('IntegrationMethod', 'POST')
        Property('PayloadFormatVersion', '2.0')
        Property('TimeoutInMillis', 30000)
    end

    Resource('Route') do
        Type('AWS::ApiGatewayV2::Route')
        Property('ApiId', Ref('Api'))
        Property('ApiKeyRequired', false)
        Property('AuthorizationType', 'NONE')
        Property('RouteKey', 'GET /amis')
        Property('Target', FnSub('integrations/${Integration}'))
    end

    Resource('LogGroup') do
        Type('AWS::Logs::LogGroup')
        Property('RetentionInDays', 7)
        Property('LogGroupName', 'http-gateway-amis')
    end

    Output('ApiUrl') do
        Value(FnSub('https://${Api}.execute-api.${AWS::Region}.amazonaws.com'))
        Export(FnSub("${EnvironmentName}-ApiUrl"))
    end

end
