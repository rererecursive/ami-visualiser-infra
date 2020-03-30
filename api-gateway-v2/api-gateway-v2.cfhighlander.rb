CfhighlanderTemplate do
  Name 'api-gateway-v2'
  Description "api-gateway-v2 - #{component_version}"

  Parameters do
    ComponentParam 'EnvironmentName', 'dev', isGlobal: true
    ComponentParam 'EnvironmentType', 'development', allowedValues: ['development','production'], isGlobal: true
    ComponentParam 'GetAmiFunctionArn'
  end


end
