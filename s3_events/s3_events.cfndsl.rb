CloudFormation do

  if defined?(notifications)
    notifications = notifications.select { |key, values| values['enabled'] }

    notifications.each do |notification_name, notification|
      lambda_notification = {
          'Bucket' =>   FnSub(notification['bucket']),
          'Function' => FnSub(notification['function']),
          'Prefix' =>   notification['prefix'],
          'Suffix' =>   notification['suffix']
      }

      Resource("S3LambdaNotification") do
        Type 'Custom::S3LambdaNotification'
        Property 'ServiceToken', Ref('S3EventsFunctionArn')
        Property 'Region', Ref('AWS::Region')
        Property 'AccountId', Ref('AWS::AccountId')
        Property 'StackName', Ref('AWS::StackName')
        Property 'LambdaNotification', lambda_notification
      end
    end
  end
end
