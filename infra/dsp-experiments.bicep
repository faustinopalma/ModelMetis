targetScope = 'resourceGroup'

param location string = 'swedencentral'
param callerPrincipalId string
param allowedIpv4 string

@minValue(1)
@maxValue(100)
param capacity int = 50

var accountName = 'aif-modelmetis-dsp-${uniqueString(resourceGroup().id)}'

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  tags: {
    project: 'modelmetis'
    environment: 'dev'
    purpose: 'bounded-dsp-reference-experiments'
    managedBy: 'bicep'
    repo: 'github.com/faustinopalma/ModelMetis'
  }
  properties: {
    customSubDomainName: accountName
    disableLocalAuth: true
    dynamicThrottlingEnabled: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
      ipRules: [
        { value: allowedIpv4 }
      ]
      virtualNetworkRules: []
    }
  }
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

resource inferenceRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
}

resource callerAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, callerPrincipalId, inferenceRole.id)
  properties: {
    principalId: callerPrincipalId
    principalType: 'User'
    roleDefinitionId: inferenceRole.id
  }
}

output accountName string = account.name
output accountId string = account.id
output deploymentName string = deployment.name
output endpoint string = 'https://${account.name}.openai.azure.com/'
