// llama_logits_qual.cpp - pinned 0faee5004297c3bcfa40b7bf11750127b8c1fd7d
#include "llama.h"
#include "ggml-backend.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <string>
#include <chrono>
#include <atomic>
#include <thread>
#include <algorithm>
#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
#else
#include <fstream>
#endif
static std::atomic<bool> g_abort{false};
static bool abort_cb(void*){return g_abort.load();}
static std::string esc(const std::string&s){std::string r;for(char c:s){if(c=='"')r+="\\\"";else if(c=='\\')r+="\\\\";else if(c=='\n')r+="\\n";else if(c=='\t')r+="\\t";else r+=c;}return r;}
static bool sha256_file(const char*p,uint8_t h[32],uint64_t&sz){
#ifdef _WIN32
HANDLE f=CreateFileA(p,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);
if(f==INVALID_HANDLE_VALUE)return false;
LARGE_INTEGER li;GetFileSizeEx(f,&li);sz=(uint64_t)li.QuadPart;
BCRYPT_ALG_HANDLE al;BCryptOpenAlgorithmProvider(&al,BCRYPT_SHA256_ALGORITHM,nullptr,0);
BCRYPT_HASH_HANDLE ha;BCryptCreateHash(al,&ha,nullptr,0,nullptr,0,0);
uint8_t buf[1<<16];DWORD rd;while(ReadFile(f,buf,sizeof(buf),&rd,nullptr)&&rd>0)BCryptHashData(ha,buf,rd,0);
DWORD hl=32;BCryptFinishHash(ha,h,hl,0);BCryptDestroyHash(ha);BCryptCloseAlgorithmProvider(al,0);CloseHandle(f);return true;
#else
std::ifstream ifs(p,std::ios::binary);if(!ifs)return false;ifs.seekg(0,std::ios::end);sz=ifs.tellg();ifs.seekg(0);
uint32_t H[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
uint64_t tot=0;uint8_t blk[64];auto R=[](uint32_t x,int n){return(x>>n)|(x<<(32-n));};
auto proc=[&](const uint8_t*b){uint32_t w[64];for(int i=0;i<16;i++)w[i]=(b[i*4]<<24)|(b[i*4+1]<<16)|(b[i*4+2]<<8)|b[i*4+3];for(int i=16;i<64;i++){uint32_t s0=R(w[i-15],7)^R(w[i-15],18)^(w[i-15]>>3);uint32_t s1=R(w[i-2],17)^R(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}uint32_t a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],hh=H[7];for(int i=0;i<64;i++){uint32_t S1=R(e,6)^R(e,11)^R(e,25);uint32_t ch=(e&f)^(~e&g);uint32_t t1=hh+S1+ch+((i<16)?(uint32_t)((i==0)?0x428a2f98:(i==1)?0x71374491:(i==2)?0xb5c0fbcf:(i==3)?0xe9b5dba5:(i==4)?0x3956c25b:(i==5)?0x59f111f1:(i==6)?0x923f82a4:(i==7)?0xab1c5ed5:(i==8)?0xd807aa98:(i==9)?0x12835b01:(i==10)?0x243185be:(i==11)?0x550c7dc3:(i==12)?0x72be5d74:(i==13)?0x80deb1fe:(i==14)?0x9bdc06a7:(i==15)?0xc19bf174:0):((i<32)?(uint32_t)((i==16)?0xe49b69c1:(i==17)?0xefbe4786:(i==18)?0x0fc19dc6:(i==19)?0x240ca1cc:(i==20)?0x2de92c6f:(i==21)?0x4a7484aa:(i==22)?0x5cb0a9dc:(i==23)?0x76f988da:(i==24)?0x983e5152:(i==25)?0xa831c66d:(i==26)?0xb00327c8:(i==27)?0xbf597fc7:(i==28)?0xc6e00bf3:(i==29)?0xd5a79147:(i==30)?0x06ca6351:(i==31)?0x14292967:0):((i<48)?(uint32_t)((i==32)?0x27b70a85:(i==33)?0x2e1b2138:(i==34)?0x4d2c6dfc:(i==35)?0x53380d13:(i==36)?0x650a7354:(i==37)?0x766a0abb:(i==38)?0x81c2c92e:(i==39)?0x92722c85:(i==40)?0xa2bfe8a1:(i==41)?0xa81a664b:(i==42)?0xc24b8b70:(i==43)?0xc76c51a3:(i==44)?0xd192e819:(i==45)?0xd6990624:(i==46)?0xf40e3585:(i==47)?0x106aa070:0):(uint32_t)((i==48)?0x19a4c116:(i==49)?0x1e376c08:(i==50)?0x2748774c:(i==51)?0x34b0bcb5:(i==52)?0x391c0cb3:(i==53)?0x4ed8aa4a:(i==54)?0x5b9cca4f:(i==55)?0x682e6ff3:(i==56)?0x748f82ee:(i==57)?0x78a5636f:(i==58)?0x84c87814:(i==59)?0x8cc70208:(i==60)?0x90befffa:(i==61)?0xa4506ceb:(i==62)?0xbef9a3f7:(i==63)?0xc67178f2:0))))+w[i];uint32_t S0=R(a,2)^R(a,13)^R(a,22);uint32_t mj=(a&b)^(a&c)^(b&c);uint32_t t2=S0+mj;hh=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}H[0]+=a;H[1]+=b;H[2]+=c;H[3]+=d;H[4]+=e;H[5]+=f;H[6]+=g;H[7]+=hh;};
while(ifs.read((char*)blk,64)){proc(blk);tot+=64;}int rem=ifs.gcount();tot+=rem;memcpy(blk,((char*)blk),rem);blk[rem]=0x80;if(rem>=56){memset(blk+rem+1,0,63-rem);proc(blk);memset(blk,0,64);}else memset(blk+rem+1,0,55-rem);uint64_t bits=tot*8;for(int i=0;i<8;i++)blk[56+i]=(bits>>(56-i*8))&0xff;proc(blk);for(int i=0;i<8;i++){h[i*4]=(H[i]>>24)&0xff;h[i*4+1]=(H[i]>>16)&0xff;h[i*4+2]=(H[i]>>8)&0xff;h[i*4+3]=H[i]&0xff;}return true;
#endif
}
struct CmpResult{double max_abs;double rmse;int fail_count;bool all_finite_ref;bool all_finite_tgt;};
static CmpResult compare_logits(const float*r,const float*t,size_t n,float atol,float rtol){
CmpResult res={0,0,0,true,true};double sum_sq=0;for(size_t i=0;i<n;i++){if(!std::isfinite(r[i]))res.all_finite_ref=false;if(!std::isfinite(t[i]))res.all_finite_tgt=false;if(!std::isfinite(r[i])||!std::isfinite(t[i]))continue;double d=std::abs((double)r[i]-t[i]);double tol=atol+rtol*std::abs((double)r[i]);if(d>tol)res.fail_count++;if(d>res.max_abs)res.max_abs=d;sum_sq+=d*d;}res.rmse=n>0?std::sqrt(sum_sq/n):0;return res;}
static void self_test(){
float r[]={1.0f,2.0f,3.0f,4.0f};float t[]={1.005f,2.005f,3.005f,4.005f};
auto c1=compare_logits(r,t,4,0.01f,0.01f);fprintf(stderr,"SELFTEST finite pass=%d\n",c1.fail_count==0);
float r2[]={1.0f,NAN,3.0f};float t2[]={1.0f,2.0f,3.0f};
auto c2=compare_logits(r2,t2,3,0.01f,0.01f);fprintf(stderr,"SELFTEST nan detected=%d\n",!c2.all_finite_ref);
float r3[]={1.0f,INFINITY,3.0f};float t3[]={1.0f,2.0f,3.0f};
auto c3=compare_logits(r3,t3,3,0.01f,0.01f);fprintf(stderr,"SELFTEST inf detected=%d\n",!c3.all_finite_ref);
float r4[]={1.0f};float t4[]={2.0f};
auto c4=compare_logits(r4,t4,1,0.01f,0.01f);fprintf(stderr,"SELFTEST shape1 fail=%d\n",c4.fail_count==1);
float r5[]={1.0f,2.0f};float t5[]={1.0f,2.0f};t5[0]+=0.05f;
auto c5=compare_logits(r5,t5,2,0.01f,0.01f);fprintf(stderr,"SELFTEST perturb fail=%d\n",c5.fail_count==1);
fprintf(stderr,"SELFTEST complete - no hardware PASS claimed\n");}
int main(int argc,char**argv){
if(argc>=2&&strcmp(argv[1],"--self-test")==0){self_test();return 0;}
std::string model_path,expected_sha,devices_arg;bool inject_corrupt=false;
for(int i=1;i<argc;i++){if(!strcmp(argv[i],"--model")&&i+1<argc)model_path=argv[++i];else if(!strcmp(argv[i],"--expected-sha256")&&i+1<argc)expected_sha=argv[++i];else if(!strcmp(argv[i],"--devices")&&i+1<argc)devices_arg=argv[++i];else if(!strcmp(argv[i],"--inject-logit-corruption"))inject_corrupt=true;}
if(model_path.empty()||expected_sha.empty()||devices_arg.empty()){fprintf(stderr,"Usage: --model P --expected-sha256 H --devices D0,D1 [--inject-logit-corruption]\n");return 2;}
if(expected_sha.size()!=64){fprintf(stderr,"SHA256 must be 64 hex chars\n");return 2;}
if(expected_sha.substr(0,4)!="9465"){fprintf(stderr,"Expected SHA prefix 9465\n");return 2;}
uint8_t hash[32];uint64_t fsz=0;if(!sha256_file(model_path.c_str(),hash,fsz)){fprintf(stderr,"Cannot read model\n");return 1;}
if(fsz!=639446688ULL){fprintf(stderr,"Size mismatch %llu\n",(unsigned long long)fsz);return 1;}
char hex[65];for(int i=0;i<32;i++)sprintf(hex+i*2,"%02x",hash[i]);hex[64]=0;
if(strcmp(hex,expected_sha.c_str())!=0){fprintf(stderr,"SHA mismatch\n");return 1;}
size_t comma=devices_arg.find(',');if(comma==std::string::npos){fprintf(stderr,"Need two devices\n");return 2;}
std::string dev0=devices_arg.substr(0,comma),dev1=devices_arg.substr(comma+1);
llama_backend_init();ggml_backend_load_all();
auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(60);
g_abort.store(false);
std::thread timer([&]{while(std::chrono::steady_clock::now()<deadline&&!g_abort.load())std::this_thread::sleep_for(std::chrono::milliseconds(100));g_abort.store(true);});
int exit_code=2;std::string qual_limit="none";std::string desc_buf(256,'\0');std::string meta_desc;
int32_t n_layer=0,n_vocab=0;std::string dtype_str="Q8_0";
struct RAII{llama_model*m=nullptr;llama_context*c=nullptr;~RAII(){if(c)llama_free(c);if(m)llama_model_free(m);}};
{
RAII cpu;
llama_model_params mp=llama_model_default_params();mp.n_gpu_layers=0;mp.devices=nullptr;mp.split_mode=LLAMA_SPLIT_MODE_NONE;
cpu.m=llama_model_load_from_file(model_path.c_str(),mp);
if(!cpu.m){fprintf(stderr,"CPU model load failed\n");exit_code=1;goto done;}
n_layer=llama_model_n_layer(cpu.m);const llama_vocab*vocab=llama_model_get_vocab(cpu.m);n_vocab=llama_vocab_n_tokens(vocab);
llama_model_desc(cpu.m,&desc_buf[0],desc_buf.size());meta_desc=esc(desc_buf.c_str());
llama_context_params cp=llama_context_default_params();cp.n_ctx=128;cp.n_batch=32;cp.n_ubatch=32;cp.n_threads=4;cp.n_threads_batch=4;cp.offload_kqv=false;cp.op_offload=false;cp.abort_callback=abort_cb;cp.abort_callback_data=nullptr;
cpu.c=llama_init_from_model(cpu.m,cp);
if(!cpu.c){fprintf(stderr,"CPU ctx failed\n");exit_code=1;goto done;}
std::vector<llama_token>tokens(16);for(int i=0;i<16;i++)tokens[i]=(llama_token)(i%(n_vocab>0?n_vocab:1));
llama_batch batch=llama_batch_init(32,0,1);batch.n_tokens=16;batch.token=tokens.data();
std::vector<llama_pos>pos(16);for(int i=0;i<16;i++)pos[i]=i;batch.pos=pos.data();
std::vector<int32_t>nseq(16,1);batch.n_seq_id=nseq.data();
std::vector<llama_seq_id*>seqp(16);std::vector<llama_seq_id>sids(16,0);for(int i=0;i<16;i++)seqp[i]=&sids[i];batch.seq_id=seqp.data();
std::vector<int8_t>logits_flag(16,0);logits_flag[15]=1;batch.logits=logits_flag.data();
if(llama_decode(cpu.c,batch)!=0){fprintf(stderr,"CPU decode failed\n");llama_batch_free(batch);exit_code=1;goto done;}
float*cpu_logit_ptr=llama_get_logits_ith(cpu.c,-1);
if(!cpu_logit_ptr){fprintf(stderr,"CPU logits null\n");llama_batch_free(batch);exit_code=1;goto done;}
std::vector<float>cpu_logits(cpu_logit_ptr,cpu_logit_ptr+n_vocab);
llama_batch_free(batch);
llama_free(cpu.c);cpu.c=nullptr;llama_model_free(cpu.m);cpu.m=nullptr;
{
ggml_backend_dev_t d0=ggml_backend_dev_by_name(dev0.c_str());
ggml_backend_dev_t d1=ggml_backend_dev_by_name(dev1.c_str());
if(!d0||!d1){fprintf(stderr,"Device lookup failed\n");qual_limit="device_not_found";exit_code=2;goto done;}
enum ggml_backend_dev_type t0=ggml_backend_dev_type(d0),t1=ggml_backend_dev_type(d1);
if(t0!=GGML_BACKEND_DEVICE_TYPE_GPU&&t0!=GGML_BACKEND_DEVICE_TYPE_IGPU){qual_limit="dev0_not_gpu";exit_code=2;goto done;}
if(t1!=GGML_BACKEND_DEVICE_TYPE_GPU&&t1!=GGML_BACKEND_DEVICE_TYPE_IGPU){qual_limit="dev1_not_gpu";exit_code=2;goto done;}
struct ggml_backend_dev_props p0,p1;ggml_backend_dev_get_props(d0,&p0);ggml_backend_dev_get_props(d1,&p1);
std::string pci0=p0.device_id?p0.device_id:"",pci1=p1.device_id?p1.device_id:"";
if(pci0.empty()||pci1.empty())qual_limit="no_pci_identity_available";
else if(pci0==pci1){qual_limit="duplicate_physical_device";exit_code=2;goto done;}
RAII gpu;
llama_model_params gmp=llama_model_default_params();gmp.n_gpu_layers=INT32_MAX;gmp.split_mode=LLAMA_SPLIT_MODE_LAYER;
size_t max_dev=llama_max_devices();std::vector<float>tsplit(max_dev>0?max_dev:2,0.0f);if(tsplit.size()>=2){tsplit[0]=1.0f;tsplit[1]=1.0f;}gmp.tensor_split=tsplit.data();
std::vector<ggml_backend_dev_t>devs={d0,d1,nullptr};gmp.devices=devs.data();
gpu.m=llama_model_load_from_file(model_path.c_str(),gmp);
if(!gpu.m){fprintf(stderr,"GPU model load failed\n");exit_code=1;goto done;}
llama_context_params gcp=llama_context_default_params();gcp.n_ctx=128;gcp.n_batch=32;gcp.n_ubatch=32;gcp.n_threads=4;gcp.n_threads_batch=4;gcp.offload_kqv=true;gcp.op_offload=true;gcp.abort_callback=abort_cb;gcp.abort_callback_data=nullptr;
gpu.c=llama_init_from_model(gpu.m,gcp);
if(!gpu.c){fprintf(stderr,"GPU ctx failed\n");exit_code=1;goto done;}
std::vector<llama_token>gtokens(16);for(int i=0;i<16;i++)gtokens[i]=(llama_token)(i%(n_vocab>0?n_vocab:1));
llama_batch gbatch=llama_batch_init(32,0,1);gbatch.n_tokens=16;gbatch.token=gtokens.data();
std::vector<llama_pos>gpos(16);for(int i=0;i<16;i++)gpos[i]=i;gbatch.pos=gpos.data();
std::vector<int32_t>gnseq(16,1);gbatch.n_seq_id=gnseq.data();
std::vector<llama_seq_id*>gseqp(16);std::vector<llama_seq_id>gsids(16,0);for(int i=0;i<16;i++)gseqp[i]=&gsids[i];gbatch.seq_id=gseqp.data();
std::vector<int8_t>glogits(16,0);glogits[15]=1;gbatch.logits=glogits.data();
if(llama_decode(gpu.c,gbatch)!=0){fprintf(stderr,"GPU decode failed\n");llama_batch_free(gbatch);exit_code=1;goto done;}
float*gpu_logit_ptr=llama_get_logits_ith(gpu.c,-1);
if(!gpu_logit_ptr){fprintf(stderr,"GPU logits null\n");llama_batch_free(gbatch);exit_code=1;goto done;}
std::vector<float>gpu_logits(gpu_logit_ptr,gpu_logit_ptr+n_vocab);
llama_batch_free(gbatch);
if(inject_corrupt&&n_vocab>0){float ref_val=cpu_logits[0];float threshold=0.01f+0.01f*std::abs(ref_val)+1.0f;gpu_logits[0]=ref_val+(threshold>0?threshold:-threshold)+0.5f;}
auto cmp=compare_logits(cpu_logits.data(),gpu_logits.data(),n_vocab,0.01f,0.01f);
if(!cmp.all_finite_ref||!cmp.all_finite_tgt){exit_code=1;}
else if(cmp.fail_count>0){exit_code=1;}
else{exit_code=0;}
char wl_hash[65];uint8_t wh[32];{uint32_t H[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};uint8_t blk[64];memset(blk,0,64);std::string inp=model_path+":"+devices_arg+":128:32:32:20261004";memcpy(blk,inp.c_str(),std::min(inp.size(),(size_t)55));blk[inp.size()]=0x80;uint64_t bits=inp.size()*8;for(int i=0;i<8;i++)blk[56+i]=(bits>>(56-i*8))&0xff;auto R=[](uint32_t x,int n){return(x>>n)|(x<<(32-n));};uint32_t w[64];for(int i=0;i<16;i++)w[i]=(blk[i*4]<<24)|(blk[i*4+1]<<16)|(blk[i*4+2]<<8)|blk[i*4+3];for(int i=16;i<64;i++){uint32_t s0=R(w[i-15],7)^R(w[i-15],18)^(w[i-15]>>3);uint32_t s1=R(w[i-2],17)^R(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}uint32_t a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],hh=H[7];static const uint32_t K[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};for(int i=0;i<64;i++){uint32_t S1=R(e,6)^R(e,11)^R(e,25);uint32_t ch=(e&f)^(~e&g);uint32_t t1=hh+S1+ch+K[i]+w[i];uint32_t S0=R(a,2)^R(a,13)^R(a,22);uint32_t mj=(a&b)^(a&c)^(b&c);uint32_t t2=S0+mj;hh=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}H[0]+=a;H[1]+=b;H[2]+=c;H[3]+=d;H[4]+=e;H[5]+=f;H[6]+=g;H[7]+=hh;for(int i=0;i<8;i++)sprintf(wh_hash_out_dummy_placeholder+i*2,"%08x",H[i]);}for(int i=0;i<8;i++)sprintf(wl_hash+i*8,"%08x",H[i]);
fprintf(stdout,"{\"status\":%d,\"model\":\"%s\",\"file_size\":%llu,\"sha256\":\"%s\",\"devices\":[\"%s\",\"%s\"],\"device_population\":%zu,\"selected_names\":[\"%s\",\"%s\"],\"workload_hash\":\"%s\",\"context\":128,\"batch\":32,\"ubatch\":32,\"n_layer\":%d,\"n_vocab\":%d,\"description\":\"%s\",\"dtype\":\"%s\",\"max_abs\":%.17g,\"rmse\":%.17g,\"fail_count\":%d,\"all_finite_ref\":%s,\"all_finite_tgt\":%s,\"inject_corruption\":%s,\"qualification_limits\":\"%s\",\"notes\":\"provisional numeric threshold atol=0.01 rtol=0.01 not universal qualification; actual operator qualification via upstream test-backend-ops separate gate; CPU fallback indication absent per-layer instrument actual ownership UNKNOWN not claim full dedicated; AMD shared not VRAM pool\"}\n",exit_code,esc(model_path).c_str(),(unsigned long long)fsz,hex,esc(dev0).c_str(),esc(dev1).c_str(),ggml_backend_dev_count(),esc(dev0).c_str(),esc(dev1).c_str(),wl_hash,n_layer,n_vocab,meta_desc.c_str(),dtype_str.c_str(),cmp.max_abs,cmp.rmse,cmp.fail_count,cmp.all_finite_ref?"true":"false",cmp.all_finite_tgt?"true":"false",inject_corrupt?"true":"false",esc(qual_limit).c_str());
}
}
done:
g_abort.store(true);timer.join();llama_backend_free();return exit_code;
}

