CfhighlanderTemplate do

  Parameters do
    ComponentParam 'EnvironmentName', 'dev', isGlobal: true
    ComponentParam 'EnvironmentType', 'development', isGlobal: true
    ComponentParam 'PutAmiFunctionArn'
    ComponentParam 'S3EventsFunctionArn'
    ComponentParam 'S3Bucket'
  end

end
