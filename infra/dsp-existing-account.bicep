targetScope = 'resourceGroup'

param accountName string = 'aif-iveco-safety-test-20260918'

@minValue(1)
@maxValue(100)
param capacity int = 50

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: 'modelmetis-dsp-sol'
  sku: {
    name: 'DataZoneStandard'
    capacity: capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5.6-sol'
      version: '2026-07-09'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

output accountId string = account.id
output deploymentName string = deployment.name
output endpoint string = 'https://${accountName}.openai.azure.com/'
