"""Independent synthetic capture fixture helpers. No candidate imports or execution."""
import hashlib,json,pathlib,struct
PIN='0faee5004297c3bcfa40b7bf11750127b8c1fd7d'
MODEL='9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031'
def digest(data):return hashlib.sha256(data).hexdigest()
def fixture_pair(folder):
 folder=pathlib.Path(folder);expected={'source_sha256':digest(b'independent-synthetic-source'),'executable_sha256':digest(b'independent-synthetic-executable'),'model_sha256':MODEL,'model_bytes':639446688,'workload_sha256':digest(b'independent-synthetic-common-run'),'devices':['Vulkan0','Vulkan1']}
 values=[0.,1000000.,-2.,3.,4.,5.,6.,7.];raw=struct.pack('<8f',*values)
 for role,name in [('CPU_REFERENCE','cpu'),('VULKAN_DIAGNOSTIC','gpu')]:
  p=folder/name;p.mkdir(parents=True,exist_ok=False);gpu=name=='gpu';origin=dict(expected);origin.update(pinned_commit=PIN,role=role,devices=expected['devices'] if gpu else [],tokens=list(range(16)),n_ctx_requested=128,n_ctx_actual=256,n_batch=32,n_ubatch=32,n_threads=4,kv_type_k='F32',kv_type_v='F32',flash_attention=False,vulkan_disable_f16=gpu,vulkan_disable_fusion=gpu)
  nodes=[]
  for i,node in enumerate(['attn_norm-0','ffn_out-0','result_output']):
   file='node_%02d.bin'%i;(p/file).write_bytes(raw);nodes.append({'ordinal':i,'name':node,'op':'NORM' if i==0 else 'ADD' if i==1 else 'MUL_MAT','dtype':'F32_LE','dims':[8,1,1,1],'strides':[4,32,32,32],'nbytes':32,'sha256':digest(raw),'file':file})
  manifest={'schema':'LLAMA_CAPTURE_V1','status':'COMPLETE','diagnostic_intrusive':True,'qualification':'DIAGNOSTIC_ONLY','origin':origin,'captures':nodes};(p/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
 return folder/'cpu',folder/'gpu',expected
