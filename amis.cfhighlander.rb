CfhighlanderTemplate do
  Name 'amis'
  Description "amis - #{component_version}"

  Parameters do
    ComponentParam 'EnvironmentName', 'dev', isGlobal: true
    ComponentParam 'EnvironmentType', 'development', allowedValues: ['development','production'], isGlobal: true
    ComponentParam 'LambdaFunctionsVersion', 'test'
    ComponentParam 'S3Bucket', 'ztlewis-builds'
    ComponentParam 'S3Prefix', 'lambdas'
  end

  Component name: 'dynamodb', template: 'dynamodb', config: dynamodb

  Component name: 'lambda', template: 'lambda', config: lambdas do
    parameter name: 'LambdaFunctionsVersion', value: Ref('LambdaFunctionsVersion')
    parameter name: 'S3Bucket', value: Ref('S3Bucket')
    parameter name: 'S3Prefix', value: Ref('S3Prefix')
    parameter name: 'DynamoDbTableName', value: cfout('dynamodb', 'TableName')
  end

  Component name: 'httpapi', template: 'api-gateway-v2' do
    parameter name: 'GetAmiFunctionArn', value: cfout('lambda', 'GetAmiArn')
  end

end
