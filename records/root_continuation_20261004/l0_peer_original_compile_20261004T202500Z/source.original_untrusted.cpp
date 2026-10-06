#include <level_zero/ze_api.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
using namespace std;
const uint64_t TMO=10000000000ULL;
const char*SEQ="zeInit,zeDriverGet,zeDeviceGet,zeDeviceGetProperties,zeDeviceGetCommandQueueGroupProperties,zeDeviceGetP2PProperties,zeContextCreate,zeMemAllocDevice,zeMemAllocHost,zeCommandQueueCreate,zeCommandListCreate,zeCommandListAppendMemoryFill,zeFenceCreate,zeCommandQueueExecuteCommandLists,zeFenceHostSynchronize,zeCommandListAppendMemoryCopy";
const char*zres(ze_result_t r){return r==ZE_RESULT_SUCCESS?"SUCCESS":(r==ZE_RESULT_ERROR_UNSUPPORTED_FEATURE?"UNSUPPORTED":(r==ZE_RESULT_ERROR_UNINITIALIZED?"UNINIT":(r==ZE_RESULT_ERROR_NOT_AVAILABLE?"NOT_AVAILABLE":"ERROR")));}
string q(const string&s){char c=34;return string(1,c)+s+string(1,c);}
string q(const char*s){return q(string(s));}
string ps(void*p){char b[32];snprintf(b,32,"%p",p);return b;}
struct Dev{ze_device_handle_t h{};ze_device_properties_t p{};string u;};
struct State{ze_context_handle_t c=nullptr;vector<void*>m;vector<ze_command_list_handle_t>l;vector<ze_command_queue_handle_t>qs;~State(){for(auto x:l)zeCommandListDestroy(x);for(auto x:qs)zeCommandQueueDestroy(x);for(auto x:m)if(x)zeMemFree(c,x);if(c)zeContextDestroy(c);}};
string us(const ze_device_uuid_t&u){char b[40];snprintf(b,40,"%08x%08x%08x%08x",u.id[0],u.id[1],u.id[2],u.id[3]);return b;}
int nc(const char*w){string o="{"+q("status")+":"+q("NOT_CHECKED")+","+q("reason")+":"+q(w)+"}";puts(o.c_str());return 2;}
int fail(const char*a,ze_result_t r){string o="{"+q("status")+":"+q("FAIL")+","+q("api")+":"+q(a)+","+q("ze_result")+":"+to_string((int)r)+","+q("ze_result_name")+":"+q(zres(r))+"}";puts(o.c_str());return 1;}
bool ncr(ze_result_t r){return r==ZE_RESULT_ERROR_UNSUPPORTED_FEATURE||r==ZE_RESULT_ERROR_UNINITIALIZED||r==ZE_RESULT_ERROR_NOT_AVAILABLE;}
struct Sel{int o=-1;string k;};
Sel pick(ze_device_handle_t d){uint32_t n=0;if(zeDeviceGetCommandQueueGroupProperties(d,&n,nullptr)||!n)return{};vector<ze_command_queue_group_properties_t>v(n);for(auto&x:v){memset(&x,0,sizeof(x));x.stype=ZE_STRUCTURE_TYPE_COMMAND_QUEUE_GROUP_PROPERTIES;}if(zeDeviceGetCommandQueueGroupProperties(d,&n,v.data()))return{};int c=-1,m=-1;for(uint32_t i=0;i<n;i++){if(v[i].flags&ZE_COMMAND_QUEUE_GROUP_PROPERTY_FLAG_COPY)c=i;if(v[i].flags&ZE_COMMAND_QUEUE_GROUP_PROPERTY_FLAG_COMPUTE)m=i;}Sel s;if(c>=0){s.o=c;s.k="COPY";}else if(m>=0){s.o=m;s.k="COMPUTE";}return s;}
int main(int argc,char**argv){string su,du;bool inj=false;for(int i=1;i<argc;i++){string a=argv[i];if(a=="--inject-corruption")inj=true;else if(su.empty())su=a;else if(du.empty())du=a;}
if(su.empty()||du.empty())return nc("usage SRC_UUID DST_UUID [--inject-corruption]");
ze_result_t r=zeInit(0);if(r)return nc("zeInit");
uint32_t nd=0;r=zeDriverGet(&nd,nullptr);if(r||!nd)return nc("zeDriverGet");vector<ze_driver_handle_t>dr(nd);r=zeDriverGet(&nd,dr.data());if(r)return fail("zeDriverGet",r);
Dev S,D;bool sf=false,df=false;ze_driver_handle_t sd=nullptr,dd=nullptr;
for(auto d:dr){uint32_t n=0;if(zeDeviceGet(d,&n,nullptr)||!n)continue;vector<ze_device_handle_t>dv(n);if(zeDeviceGet(d,&n,dv.data()))continue;for(auto h:dv){ze_device_properties_t p{};p.stype=ZE_STRUCTURE_TYPE_DEVICE_PROPERTIES;if(zeDeviceGetProperties(h,&p))continue;if(p.type!=ZE_DEVICE_TYPE_GPU)continue;string u=us(p.uuid);if(u==su){S.h=h;S.p=p;S.u=u;sd=d;sf=true;}if(u==du){D.h=h;D.p=p;D.u=u;dd=d;df=true;}}}
if(!sf||!df)return nc("selected UUID not enumerated");
if(sd!=dd)return nc("selected devices not under same driver");
if(S.p.vendorId!=0x8086u||D.p.vendorId!=0x8086u)return nc("selected device not Intel");
if(S.u==D.u)return nc("same device selected");
ze_device_p2p_properties_t pp{};pp.stype=ZE_STRUCTURE_TYPE_DEVICE_P2P_PROPERTIES;bool s2d=false,d2s=false;
r=zeDeviceGetP2PProperties(S.h,D.h,&pp);if(r==ZE_RESULT_SUCCESS)s2d=pp.flags&ZE_DEVICE_P2P_PROPERTY_FLAG_ACCESS;
r=zeDeviceGetP2PProperties(D.h,S.h,&pp);if(r==ZE_RESULT_SUCCESS)d2s=pp.flags&ZE_DEVICE_P2P_PROPERTY_FLAG_ACCESS;
if(!s2d&&!d2s)return nc("directed peer access unsupported");
State st;ze_context_desc_t cd{};cd.stype=ZE_STRUCTURE_TYPE_CONTEXT_DESC;r=zeContextCreate(sd,&cd,&st.c);if(r)return ncr(r)?nc("zeContextCreate"):fail("zeContextCreate",r);
const size_t B=65536;ze_device_mem_alloc_desc_t dm{};dm.stype=ZE_STRUCTURE_TYPE_DEVICE_MEM_ALLOC_DESC;dm.ordinal=0;void*sp=nullptr,*dp=nullptr,*hp=nullptr;
r=zeMemAllocDevice(st.c,&dm,B,1,S.h,&sp);if(r)return ncr(r)?nc("src alloc"):fail("src alloc",r);st.m.push_back(sp);
r=zeMemAllocDevice(st.c,&dm,B,1,D.h,&dp);if(r)return ncr(r)?nc("dst alloc"):fail("dst alloc",r);st.m.push_back(dp);
ze_host_mem_alloc_desc_t hm{};hm.stype=ZE_STRUCTURE_TYPE_HOST_MEM_ALLOC_DESC;r=zeMemAllocHost(st.c,&hm,B,1,&hp);if(r)return ncr(r)?nc("host alloc"):fail("host alloc",r);st.m.push_back(hp);
Sel fq=pick(S.h);if(fq.o<0)return nc("no src queue");ze_command_queue_desc_t qd{};qd.stype=ZE_STRUCTURE_TYPE_COMMAND_QUEUE_DESC;qd.ordinal=fq.o;ze_command_queue_handle_t qh=nullptr;r=zeCommandQueueCreate(st.c,S.h,fq.o,&qd,&qh);if(r)return fail("fill queue",r);st.qs.push_back(qh);
ze_command_list_desc_t ld{};ld.stype=ZE_STRUCTURE_TYPE_COMMAND_LIST_DESC;ld.commandQueueGroupOrdinal=fq.o;ze_command_list_handle_t lh=nullptr;r=zeCommandListCreate(st.c,S.h,&ld,&lh);if(r)return fail("fill list",r);st.l.push_back(lh);
uint32_t pat=0x5A5A5A5Au;r=zeCommandListAppendMemoryFill(lh,sp,&pat,sizeof(pat),B,nullptr,0,nullptr);if(r)return fail("fill",r);
r=zeCommandListClose(lh);if(r)return fail("close fill",r);ze_fence_desc_t fd{};fd.stype=ZE_STRUCTURE_TYPE_FENCE_DESC;ze_fence_handle_t fe=nullptr;r=zeFenceCreate(qh,&fd,&fe);if(r)return fail("fill fence",r);
r=zeCommandQueueExecuteCommandLists(qh,1,&lh,fe);if(r==ZE_RESULT_SUCCESS)r=zeFenceHostSynchronize(fe,TMO);zeFenceDestroy(fe);if(r)return fail("fill wait",r);
if(inj){ze_command_list_handle_t cl=nullptr;r=zeCommandListCreate(st.c,S.h,&ld,&cl);if(r)return fail("corrupt list",r);st.l.push_back(cl);uint32_t bad=0xDEADBEEFu;r=zeCommandListAppendMemoryFill(cl,sp,&bad,sizeof(bad),B,nullptr,0,nullptr);if(r)return fail("corrupt fill",r);r=zeCommandListClose(cl);if(r)return fail("close corrupt",r);ze_fence_handle_t cf=nullptr;r=zeFenceCreate(qh,&fd,&cf);if(r)return fail("corrupt fence",r);r=zeCommandQueueExecuteCommandLists(qh,1,&cl,cf);if(r==ZE_RESULT_SUCCESS)r=zeFenceHostSynchronize(cf,TMO);zeFenceDestroy(cf);if(r)return fail("corrupt wait",r);}
ze_device_handle_t cdv=s2d?S.h:D.h;const char*cdn=s2d?"src":"dst";Sel cq=pick(cdv);if(cq.o<0)return nc("no copy queue");qd.ordinal=cq.o;ze_command_queue_handle_t cqh=nullptr;r=zeCommandQueueCreate(st.c,cdv,cq.o,&qd,&cqh);if(r)return fail("copy queue",r);st.qs.push_back(cqh);
ld.commandQueueGroupOrdinal=cq.o;ze_command_list_handle_t cpl=nullptr;r=zeCommandListCreate(st.c,cdv,&ld,&cpl);if(r)return fail("copy list",r);st.l.push_back(cpl);
r=zeCommandListAppendMemoryCopy(cpl,dp,sp,B,nullptr,0,nullptr);if(r)return fail("peer copy",r);r=zeCommandListClose(cpl);if(r)return fail("close copy",r);ze_fence_handle_t cp=nullptr;r=zeFenceCreate(cqh,&fd,&cp);if(r)return fail("copy fence",r);r=zeCommandQueueExecuteCommandLists(cqh,1,&cpl,cp);if(r==ZE_RESULT_SUCCESS)r=zeFenceHostSynchronize(cp,TMO);zeFenceDestroy(cp);if(r)return fail("peer copy wait",r);
Sel rq=pick(D.h);if(rq.o<0)return nc("no dst queue");qd.ordinal=rq.o;ze_command_queue_handle_t rqh=nullptr;r=zeCommandQueueCreate(st.c,D.h,rq.o,&qd,&rqh);if(r)return fail("read queue",r);st.qs.push_back(rqh);
ld.commandQueueGroupOrdinal=rq.o;ze_command_list_handle_t rl=nullptr;r=zeCommandListCreate(st.c,D.h,&ld,&rl);if(r)return fail("read list",r);st.l.push_back(rl);
r=zeCommandListAppendMemoryCopy(rl,hp,dp,B,nullptr,0,nullptr);if(r)return fail("readback",r);r=zeCommandListClose(rl);if(r)return fail("close read",r);ze_fence_handle_t rf=nullptr;r=zeFenceCreate(rqh,&fd,&rf);if(r)return fail("read fence",r);r=zeCommandQueueExecuteCommandLists(rqh,1,&rl,rf);if(r==ZE_RESULT_SUCCESS)r=zeFenceHostSynchronize(rf,TMO);zeFenceDestroy(rf);if(r)return fail("read wait",r);
uint32_t*hw=(uint32_t*)hp;size_t bi=0;bool ok=true;for(size_t i=0;i<B/4;i++)if(hw[i]!=pat){ok=false;bi=i;break;}
if(!ok){string o="{"+q("status")+":"+q("FAIL")+","+q("reason")+":"+q("payload_mismatch")+","+q("bad_index")+":"+to_string(bi)+","+q("expected")+":"+to_string(pat)+","+q("got")+":"+to_string(hw[bi])+","+q("inject_corruption")+":"+(inj?"true":"false")+","+q("exit_code")+":1}";puts(o.c_str());return 1;}
string o="{"+q("status")+":"+q("PEER_COPY_PAYLOAD_OBSERVED")+","+q("exit_code")+":0,"+q("inject_corruption")+":"+(inj?"true":"false")+","+q("bytes")+":"+to_string(B)+","+q("words")+":"+to_string(B/4)+","+q("timeout_ns")+":"+to_string(TMO);
o+=","+q("src")+":"+"{"+q("uuid")+":"+q(S.u)+","+q("vendorId")+":"+q("0x8086")+","+q("deviceId")+":"+to_string(S.p.deviceId)+"}";
o+=","+q("dst")+":"+"{"+q("uuid")+":"+q(D.u)+","+q("vendorId")+":"+q("0x8086")+","+q("deviceId")+":"+to_string(D.p.deviceId)+"}";
o+=","+q("peer")+":"+"{"+q("src_to_dst")+":"+(s2d?"true":"false")+","+q("dst_to_src")+":"+(d2s?"true":"false")+","+q("copy_device")+":"+q(cdn)+"}";
o+=","+q("queues")+":"+"{"+q("fill")+":"+"{"+q("ordinal")+":"+to_string(fq.o)+","+q("kind")+":"+q(fq.k)+"}";
o+=","+q("copy")+":"+"{"+q("device")+":"+q(cdn)+","+q("ordinal")+":"+to_string(cq.o)+","+q("kind")+":"+q(cq.k)+"}";
o+=","+q("readback")+":"+"{"+q("ordinal")+":"+to_string(rq.o)+","+q("kind")+":"+q(rq.k)+"}}";
o+=","+q("allocations")+":"+"{"+q("src")+":"+"{"+q("ptr")+":"+q(ps(sp))+","+q("bytes")+":"+to_string(B)+","+q("owner")+":"+q(S.u)+","+q("api")+":"+q("zeMemAllocDevice")+"}";
o+=","+q("dst")+":"+"{"+q("ptr")+":"+q(ps(dp))+","+q("bytes")+":"+to_string(B)+","+q("owner")+":"+q(D.u)+","+q("api")+":"+q("zeMemAllocDevice")+"}";
o+=","+q("host")+":"+"{"+q("ptr")+":"+q(ps(hp))+","+q("bytes")+":"+to_string(B)+","+q("owner")+":null,"+q("api")+":"+q("zeMemAllocHost")+"}}";
o+=","+q("api_sequence")+":"+q(SEQ)+"}";
puts(o.c_str());return 0;}