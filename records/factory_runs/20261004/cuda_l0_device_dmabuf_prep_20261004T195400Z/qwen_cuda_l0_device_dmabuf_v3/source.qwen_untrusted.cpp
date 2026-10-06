#include <cuda.h>
#include <level_zero/ze_api.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <unistd.h>
#include <sys/stat.h>
#include <vector>
#define PAYLOAD 65536
#define WORDS 16384
#define PATTERN 0x3C6EF35Fu
#define CORRUPT_INDEX 1234
#define CORRUPT_VAL (PATTERN ^ 0x0BADF00Du)
#define TIMEOUT_NS 10000000000ULL
#define NL() putchar(10)
#define KV2(k,v) do{printf("%s=%s",#k,#v);NL();}while(0)
#define KVL(k,v) do{printf("%s=%lld",#k,(long long)(v));NL();}while(0)
#define S(a,b,c) stop(#a,#b,(long)(c))
// direct_transport_qualified=false bare_query_p2p_false=true cleanup_unknown=false
static int hexv(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
static bool parse_uuid(const char*s,uint8_t out[16]){int n=0;for(int i=0;s[i];){if(s[i]=='-'||s[i]==':'){i++;continue;}int hi=hexv(s[i++]);if(hi<0)return false;if(!s[i])return false;int lo=hexv(s[i++]);if(lo<0)return false;if(n>=16)return false;out[n++]=(uint8_t)((hi<<4)|lo);}return n==16;}
static bool uuid_eq(const uint8_t*a,const void*b){return memcmp(a,b,16)==0;}
int main(int argc,char**argv){alarm(30);
CUdevice cdev=0;CUcontext cctx=nullptr;CUdeviceptr dptr=0;int import_fd=-1;
ze_driver_handle_t zdrv=nullptr;ze_device_handle_t zdev=nullptr;ze_context_handle_t zctx=nullptr;void*imp=nullptr;void*tgt=nullptr;void*host=nullptr;
ze_command_list_handle_t cmd=nullptr;ze_command_queue_handle_t q=nullptr;ze_fence_handle_t fence=nullptr;ze_event_pool_handle_t pool=nullptr;ze_event_handle_t ev=nullptr;
auto cleanup=[&](){if(cmd)zeCommandListDestroy(cmd);if(fence)zeFenceDestroy(fence);if(ev)zeEventDestroy(ev);if(pool)zeEventPoolDestroy(pool);if(q)zeCommandQueueDestroy(q);if(host&&zctx)zeMemFree(zctx,host);if(tgt&&zctx)zeMemFree(zctx,tgt);if(imp&&zctx)zeMemFree(zctx,imp);if(zctx)zeContextDestroy(zctx);if(import_fd>=0)close(import_fd);if(dptr)cuMemFree(dptr);if(cctx)cuCtxDestroy(cctx);};
auto stop=[&](const char*status,const char*stage,long code){cleanup();printf("status=%s",status);NL();printf("stage=%s",stage);NL();printf("code=%ld",code);NL();KV2(direct_transport_qualified,false);KV2(bare_query_p2p_false,true);KV2(scope,PAYLOAD_EXPERIMENT_ONLY);KV2(cleanup_unknown,false);exit(1);};
const char*cua=nullptr;const char*inu=nullptr;bool inj=false;bool has_cua=false,has_inu=false,has_inj=false,has_dir=false;
for(int i=1;i<argc;i++){const char*a=argv[i];
if(!strcmp(a,"--inject-corruption")){if(has_inj)S(REFUSED,duplicate_option,1);has_inj=true;inj=true;continue;}
if(!strncmp(a,"--cuda-uuid=",12)){if(has_cua)S(REFUSED,duplicate_option,1);cua=a+12;if(!*cua)S(REFUSED,wrong_flag,1);has_cua=true;continue;}
if(!strncmp(a,"--intel-uuid=",13)){if(has_inu)S(REFUSED,duplicate_option,1);inu=a+13;if(!*inu)S(REFUSED,wrong_flag,1);has_inu=true;continue;}
if(!strncmp(a,"--direction=",12)){if(has_dir)S(REFUSED,duplicate_option,1);const char*d=a+12;if(!*d)S(REFUSED,wrong_flag,1);if(strcmp(d,"cuda_to_levelzero")){if(!strcmp(d,"levelzero_to_cuda"))S(NOT_CHECKED,reverse_direction_not_implemented,1);S(REFUSED,wrong_direction,1);}has_dir=true;continue;}
S(REFUSED,unknown_option,1);}
if(!cua)S(REFUSED,no_cuda_uuid,1);if(!inu)S(REFUSED,no_intel_root,1);
uint8_t cuuid[16],iuuid[16];if(!parse_uuid(cua,cuuid))S(REFUSED,bad_cuda_uuid,1);if(!parse_uuid(inu,iuuid))S(REFUSED,bad_intel_uuid,1);if(memcmp(cuuid,iuuid,16)==0)S(REFUSED,same_physical_alias,1);
CUresult r=cuInit(0);if(r)S(NOT_CHECKED,cuda_init,r);
int driverVersion=0;CUresult vr=cuDriverGetVersion(&driverVersion);if(vr)S(NOT_CHECKED,cuda_driver_version,vr);
int devCount=0;r=cuDeviceGetCount(&devCount);if(r)S(NOT_CHECKED,cuda_count,r);int cmatches=0;for(int i=0;i<devCount;i++){CUuuid u;if(cuDeviceGetUuid(&u,i)==CUDA_SUCCESS&&uuid_eq(cuuid,u.bytes)){cmatches++;cdev=i;if(cmatches>1)S(REFUSED,cuda_uuid_alias,1);}}
if(cmatches!=1)S(NOT_CHECKED,no_cuda_device,cmatches);
r=cuCtxCreate(&cctx,0,cdev);if(r)S(NOT_CHECKED,cuda_ctx,r);
int major=0,minor=0,dma=0;r=cuDeviceGetAttribute(&major,CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR,cdev);if(r)S(NOT_CHECKED,cuda_cap_attr,r);r=cuDeviceGetAttribute(&minor,CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR,cdev);if(r)S(NOT_CHECKED,cuda_cap_attr,r);r=cuDeviceGetAttribute(&dma,CU_DEVICE_ATTRIBUTE_DMA_BUF_SUPPORTED,cdev);if(r||dma!=1)S(NOT_CHECKED,cuda_dma_attr,r?r:-1);
int pcidom=-1,pcibus=-1,pcidev=-1;cuDeviceGetAttribute(&pcidom,CU_DEVICE_ATTRIBUTE_PCI_DOMAIN_ID,cdev);cuDeviceGetAttribute(&pcibus,CU_DEVICE_ATTRIBUTE_PCI_BUS_ID,cdev);cuDeviceGetAttribute(&pcidev,CU_DEVICE_ATTRIBUTE_PCI_DEVICE_ID,cdev);
long psz=sysconf(_SC_PAGESIZE);if(psz<=0)S(FAIL1,page_size,-1);size_t page=(size_t)psz;size_t actual=(PAYLOAD+page-1)&~(page-1);if(actual<PAYLOAD||actual>1048576)S(FAIL1,actual_size,-1);
r=cuMemAlloc(&dptr,actual);if(r)S(FAIL1,cuda_alloc,r);
CUdeviceptr base=0;size_t rng=0;r=cuMemGetAddressRange(&base,&rng,dptr);if(r||base!=dptr||(base%page)!=0||rng<actual||(rng%page)!=0||rng>1048576)S(FAIL1,cuda_range,r?r:-1);
unsigned int mt=0;r=cuPointerGetAttribute(&mt,CU_POINTER_ATTRIBUTE_MEMORY_TYPE,dptr);if(r||mt!=CU_MEMORYTYPE_DEVICE)S(FAIL1,cuda_host_class,r?r:(long)mt);
std::vector<uint32_t> expected(WORDS,PATTERN);
r=cuMemsetD32(dptr,PATTERN,WORDS);if(r)S(FAIL1,cuda_producer,r);if(inj){r=cuMemsetD32(dptr+CORRUPT_INDEX*sizeof(uint32_t),CORRUPT_VAL,1);if(r)S(FAIL1,cuda_producer_fault,r);}
r=cuCtxSynchronize();if(r)S(FAIL1,cuda_sync,r);
int export_fd=-1;CUresult export_res=cuMemGetHandleForAddressRange(&export_fd,base,actual,CU_MEM_RANGE_HANDLE_TYPE_DMA_BUF_FD,CU_MEM_RANGE_FLAG_DMA_BUF_MAPPING_TYPE_PCIE);if(export_res)S(NOT_CHECKED,cuda_export,export_res);import_fd=export_fd;
struct stat st;if(fstat(import_fd,&st)!=0)S(FAIL1,fstat,-1);long long fd_size=(long long)st.st_size;int dup_fd=dup(import_fd);close(import_fd);import_fd=dup_fd;if(import_fd<0)S(FAIL1,dup,-1);
ze_result_t zr=zeInit(0);if(zr!=ZE_RESULT_SUCCESS)S(NOT_CHECKED,l0_init,zr);uint32_t drvCount=0;zr=zeDriverGet(&drvCount,nullptr);if(zr!=ZE_RESULT_SUCCESS||!drvCount)S(NOT_CHECKED,l0_drivers,zr);std::vector<ze_driver_handle_t> drivers(drvCount);zr=zeDriverGet(&drvCount,drivers.data());if(zr!=ZE_RESULT_SUCCESS)S(NOT_CHECKED,l0_drivers,zr);
int lmatches=0;bool sub_alias=false;uint32_t lvendor=0,ldevice=0;for(auto dr:drivers){uint32_t dc=0;if(zeDeviceGet(dr,&dc,nullptr)!=ZE_RESULT_SUCCESS||!dc)continue;std::vector<ze_device_handle_t> devs(dc);if(zeDeviceGet(dr,&dc,devs.data())!=ZE_RESULT_SUCCESS)continue;for(auto dv:devs){ze_device_properties_t p{};p.stype=ZE_STRUCTURE_TYPE_DEVICE_PROPERTIES;if(zeDeviceGetProperties(dv,&p)!=ZE_RESULT_SUCCESS)continue;if(uuid_eq(iuuid,p.uuid.id)){lmatches++;zdrv=dr;zdev=dv;lvendor=p.vendorId;ldevice=p.deviceId;}uint32_t sc=0;if(zeDeviceGetSubDevices(dv,&sc,nullptr)==ZE_RESULT_SUCCESS&&sc){std::vector<ze_device_handle_t> subs(sc);if(zeDeviceGetSubDevices(dv,&sc,subs.data())==ZE_RESULT_SUCCESS){for(auto sd:subs){ze_device_properties_t sp{};sp.stype=ZE_STRUCTURE_TYPE_DEVICE_PROPERTIES;if(zeDeviceGetProperties(sd,&sp)==ZE_RESULT_SUCCESS&&uuid_eq(iuuid,sp.uuid.id))sub_alias=true;}}}}}
if(sub_alias)S(REFUSED,l0_subdevice_alias,1);if(lmatches==0)S(NOT_CHECKED,no_intel_root,1);if(lmatches>1)S(REFUSED,l0_root_alias,1);if(lvendor!=0x8086)S(REFUSED,wrong_gpu_vendor,lvendor);
ze_device_external_memory_properties_t ep{};ep.stype=ZE_STRUCTURE_TYPE_DEVICE_EXTERNAL_MEMORY_PROPERTIES;zr=zeDeviceGetExternalMemoryProperties(zdev,&ep);if(zr!=ZE_RESULT_SUCCESS)S(NOT_CHECKED,l0_ext_props,zr);if((ep.memoryImportSupported&ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF)==0)S(NOT_CHECKED,l0_dma_import_cap,-1);
ze_context_desc_t cd{};cd.stype=ZE_STRUCTURE_TYPE_CONTEXT_DESC;zr=zeContextCreate(zdrv,&cd,&zctx);if(zr!=ZE_RESULT_SUCCESS)S(NOT_CHECKED,l0_context,zr);
ze_external_memory_import_fd_t ifd{};ifd.stype=ZE_STRUCTURE_TYPE_EXTERNAL_MEMORY_IMPORT_FD;ifd.type=ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF;ifd.fd=import_fd;ze_device_mem_alloc_desc_t dd{};dd.stype=ZE_STRUCTURE_TYPE_DEVICE_MEM_ALLOC_DESC;dd.pNext=&ifd;ze_result_t import_res=zeMemAllocDevice(zctx,&dd,actual,0,zdev,&imp);if(import_res!=ZE_RESULT_SUCCESS){if(import_fd>=0){close(import_fd);import_fd=-1;}S(NOT_CHECKED,l0_import,import_res);}import_fd=-1;
ze_memory_allocation_properties_t ap{};ap.stype=ZE_STRUCTURE_TYPE_MEMORY_ALLOCATION_PROPERTIES;ze_device_handle_t apdev=nullptr;zr=zeMemGetAllocProperties(zctx,imp,&ap,&apdev);if(zr!=ZE_RESULT_SUCCESS||ap.type!=ZE_MEMORY_TYPE_DEVICE)S(FAIL1,host_alloc_class,zr?zr:(ze_result_t)ap.type);
uint32_t qcount=0;zr=zeDeviceGetCommandQueueGroupProperties(zdev,&qcount,nullptr);if(zr!=ZE_RESULT_SUCCESS||!qcount)S(NOT_CHECKED,l0_queue_groups,zr);std::vector<ze_command_queue_group_properties_t> qps(qcount);for(auto&x:qps)x.stype=ZE_STRUCTURE_TYPE_COMMAND_QUEUE_GROUP_PROPERTIES;zr=zeDeviceGetCommandQueueGroupProperties(zdev,&qcount,qps.data());if(zr!=ZE_RESULT_SUCCESS)S(NOT_CHECKED,l0_queue_groups,zr);int ordinal=-1;for(uint32_t i=0;i<qcount;i++){if(qps[i].numQueues&&(qps[i].flags&(ZE_COMMAND_QUEUE_GROUP_COPY_BIT|ZE_COMMAND_QUEUE_GROUP_COMPUTE_BIT))){ordinal=(int)i;break;}}if(ordinal<0)S(NOT_CHECKED,l0_queue_group,-1);
ze_device_mem_alloc_desc_t td{};td.stype=ZE_STRUCTURE_TYPE_DEVICE_MEM_ALLOC_DESC;zr=zeMemAllocDevice(zctx,&td,actual,0,zdev,&tgt);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_target,zr);
ze_host_mem_alloc_desc_t hd{};hd.stype=ZE_STRUCTURE_TYPE_HOST_MEM_ALLOC_DESC;zr=zeMemAllocHost(zctx,&hd,actual,&host);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_host,zr);memset(host,0,actual);
ze_command_list_desc_t ld{};ld.stype=ZE_STRUCTURE_TYPE_COMMAND_LIST_DESC;ld.commandQueueGroupOrdinal=ordinal;zr=zeCommandListCreate(zdev,&ld,&cmd);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_cmdlist,zr);
ze_event_pool_desc_t epd{};epd.stype=ZE_STRUCTURE_TYPE_EVENT_POOL_DESC;epd.flags=ZE_EVENT_POOL_FLAG_HOST_VISIBLE;epd.count=1;zr=zeEventPoolCreate(zctx,&epd,1,&pool);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_eventpool,zr);
ze_event_desc_t ed{};ed.stype=ZE_STRUCTURE_TYPE_EVENT_DESC;ed.index=0;ed.signal=ZE_EVENT_SCOPE_FLAG_HOST;ed.wait=ZE_EVENT_SCOPE_FLAG_HOST;zr=zeEventCreate(pool,&ed,&ev);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_event,zr);
zr=zeCommandListAppendMemoryCopy(cmd,tgt,imp,actual,nullptr,0,nullptr);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_copy_in,zr);zr=zeCommandListAppendBarrier(cmd,nullptr,0,nullptr);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_barrier,zr);zr=zeCommandListAppendMemoryCopy(cmd,host,tgt,PAYLOAD,ev,0,nullptr);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_copy_out,zr);zr=zeCommandListClose(cmd);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_close,zr);
ze_command_queue_desc_t qd{};qd.stype=ZE_STRUCTURE_TYPE_COMMAND_QUEUE_DESC;qd.ordinal=ordinal;qd.mode=ZE_COMMAND_QUEUE_MODE_DEFAULT;qd.priority=ZE_COMMAND_QUEUE_PRIORITY_NORMAL;zr=zeCommandQueueCreate(zdev,&qd,&q);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_queue,zr);
ze_fence_desc_t fd{};fd.stype=ZE_STRUCTURE_TYPE_FENCE_DESC;zr=zeFenceCreate(q,&fd,&fence);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_fence,zr);
ze_result_t exec_res=zeCommandQueueExecuteCommandLists(q,1,&cmd,fence);if(exec_res!=ZE_RESULT_SUCCESS)S(FAIL1,l0_exec,exec_res);ze_result_t sync_res=zeFenceHostSynchronize(fence,TIMEOUT_NS);if(sync_res!=ZE_RESULT_SUCCESS)S(FAIL1,l0_fence_sync,sync_res);zr=zeEventHostSynchronize(ev,TIMEOUT_NS);if(zr!=ZE_RESULT_SUCCESS)S(FAIL1,l0_event_sync,zr);
size_t mismatches=0;long first=-1;uint32_t obs=0;uint32_t*hp=(uint32_t*)host;for(size_t i=0;i<WORDS;i++){if(hp[i]!=expected[i]){if(!mismatches){first=(long)i;obs=hp[i];}mismatches++;}}
auto report=[&](const char*status,const char*stage){printf("status=%s",status);NL();printf("stage=%s",stage);NL();KV2(scope,PAYLOAD_EXPERIMENT_ONLY);KV2(direct_transport_qualified,false);KV2(bare_query_p2p_false,true);KVL(payload_bytes,PAYLOAD);KVL(actual_bytes,actual);KVL(words,WORDS);KVL(mismatches,mismatches);KVL(first_mismatch,first);KVL(observed,obs);KVL(expected_pattern,PATTERN);KVL(corrupt_index,CORRUPT_INDEX);KVL(corrupt_value,CORRUPT_VAL);KVL(inject,inj?1:0);KVL(cuda_driver,driverVersion);KVL(cuda_compute_major,major);KVL(cuda_compute_minor,minor);KVL(cuda_mem_type,mt);KVL(cuda_export_api,export_res);KVL(l0_import_api,import_res);KVL(l0_exec_api,exec_res);KVL(l0_sync_api,sync_res);KVL(l0_alloc_type,ap.type);KVL(fd_size,fd_size);KV2(fd_policy,dup_export_transfer_import_fd);KVL(l0_vendor,lvendor);KVL(l0_device,ldevice);KVL(cuda_pci_domain,pcidom);KVL(cuda_pci_bus,pcibus);KVL(cuda_pci_device,pcidev);printf("cuda_uuid_arg=%s",cua);NL();printf("intel_uuid_arg=%s",inu);NL();KV2(reversed_direction,no);KV2(no_intel_root_guard,yes);KV2(cleanup_unknown,false);};
cleanup();if(inj){if(mismatches==1&&(size_t)first==CORRUPT_INDEX&&obs==CORRUPT_VAL){report("FAIL1","corruption_detected");return 1;}report("FAIL1","corruption_unexpected");return 1;}if(mismatches){report("FAIL1","parity_mismatch");return 1;}report("PAYLOAD_EXPERIMENT_ONLY","payload_match");return 0;}