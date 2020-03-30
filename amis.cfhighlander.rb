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

  Component name: 'lambda', template: 'lambda', config: lambdas do
    parameter name: 'LambdaFunctionsVersion', value: Ref('LambdaFunctionsVersion')
    parameter name: 'S3Bucket', value: Ref('S3Bucket')
    parameter name: 'S3Prefix', value: Ref('S3Prefix')
  end

  Component name: 'httpapi', template: 'api-gateway-v2' do
    parameter name: 'GetAmiFunctionArn', value: cfout('lambda', 'GetAmiArn')
  end

end

=begin

make update Key1=Value1 Key2=Value2

1. Get existing params and replace values with UsePreviousValue: true > current.json
2. Create JSON file with input params > new.json
3. Merge current.json on top of new.json

OR

1. Get existing params > A
2. Replace all 'ParameterValue' with 'UsePreviousValue -> True' > B
    jq '.[] | .["UsePreviousValue"] = true | del(.ParameterValue)' current.json
3. For each '_PARAM_' var, print as JSON > C
    jq -n '[env | to_entries[] | select(.key | startswith("_PARAM_")) |  {"ParameterKey":(.key | sub("_PARAM_";"")), "ParameterValue":.value}]'
    jq -n '[env | to_entries[] | select(.key | startswith("")) | {"ParameterKey":.key, "ParameterValue":.value}]'
    # jq -n 'env | to_entries[] | select(.key | startswith("")) | {"ParameterKey":.key, "ParameterValue":.value}' | sed 's/^}/},/g' | sed '$ s/.$/\]/' | sed  '1s/^/\[/'
4. Merge C on top of B
    jq -s '[ .[0] + .[1]  | group_by(.ParameterKey)[] | add ]' current.json new.json

Hmm.. all params will be specified. We only want to change NEW values (those that don't match).

{
  "ParameterKey": "string",
  "ParameterValue": "string",
  "UsePreviousValue": true|false
}

{
    "ParameterKey": "LambdaFunctionsVersion",
    "ParameterValue": "test"
},
{
    "ParameterKey": "EnvironmentType",
    "ParameterValue": "development"
},
{
    "ParameterKey": "S3Bucket",
    "ParameterValue": "ztlewis-builds"
},
{
    "ParameterKey": "EnvironmentName",
    "ParameterValue": "dev"
},
{
    "ParameterKey": "S3Prefix",
    "ParameterValue": "lambdas"
}
=end