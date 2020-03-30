CloudFormation do
  ## Add your cfndsl resources here
    DynamoDB_Table("Table") do
        AttributeDefinitions [{
            AttributeName: 'id',
            AttributeType: 'S'
        }]
        KeySchema [{
            AttributeName: 'id',
            KeyType: 'HASH'
        }]
        ProvisionedThroughput({
            ReadCapacityUnits: 5,
            WriteCapacityUnits: 5
        })
        TableName table_name
    end

    Output('TableName') do
        Value(table_name)
        Export(FnSub("${EnvironmentName}-DynamoDb-TableName"))
    end
end

