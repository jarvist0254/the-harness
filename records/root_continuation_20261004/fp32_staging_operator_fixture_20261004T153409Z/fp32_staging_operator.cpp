// Independent draft test apparatus. NOT_COMPILED, NOT_EXECUTED.
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

constexpr int K=64,M=32,N=32,B=2;
constexpr size_t TENSOR_CAP=1u<<20,FIXTURE_CAP=16u<<20;
constexpr double ATOL=2e-5,RTOL=2e-6;
struct Refusal:std::runtime_error { using std::runtime_error::runtime_error; };
struct Resources {
 ggml_context *ctx=nullptr; ggml_backend_buffer_t buffer=nullptr;
 ~Resources(){if(buffer)ggml_backend_buffer_free(buffer);if(ctx)ggml_free(ctx);}
};
struct Backend {ggml_backend_t value=nullptr;~Backend(){if(value)ggml_backend_free(value);}};
std::string quote(const char *s){std::string out="\"";for(unsigned char c:std::string(s?s:"UNKNOWN")){if(c=='"'||c=='\\'){out+='\\';out+=c;}else if(c<32)out+='?';else out+=c;}return out+'"';}
float input(int k,int row,int batch,bool y){
 // Shared k-dependent signs prevent dot-product cancellation. Values discriminate F16 storage rounding.
 const float magnitude=(y?1.0002f:1.0001f)+float(k%7)*.000017f+float(row%4)*.015625f+float(batch)*.03125f;
 return k%5==0 ? -magnitude : magnitude;
}
struct Matrix {ggml_tensor *base=nullptr,*view=nullptr;std::vector<float> bytes;};
Matrix matrix(ggml_context *ctx,int rows,int layout,bool y){
 Matrix a;
 if(layout==1){ // Physical [rows,K,B] -> logical [K,rows,B]; genuine noncontiguous dim01.
  a.base=ggml_new_tensor_4d(ctx,GGML_TYPE_F32,rows,K,B,1);a.view=ggml_transpose(ctx,a.base);
 }else if(layout==2){ // Physical padded row/slice pitch; logical [K,rows,B].
  a.base=ggml_new_tensor_4d(ctx,GGML_TYPE_F32,K+4,rows,B,1);
  a.view=ggml_view_4d(ctx,a.base,K,rows,B,1,a.base->nb[1],a.base->nb[2],a.base->nb[3],0);
 }else{a.base=ggml_new_tensor_4d(ctx,GGML_TYPE_F32,K,rows,B,1);a.view=a.base;}
 if(!a.base||!a.view)throw Refusal("tensor construction");
 const size_t size=ggml_nbytes(a.base);if(size>TENSOR_CAP||size%4)throw Refusal("tensor byte cap");
 a.bytes.assign(size/4,0.0f);
 for(int b=0;b<B;++b)for(int row=0;row<rows;++row)for(int k=0;k<K;++k){
  const size_t offset=size_t(k)*a.view->nb[0]+size_t(row)*a.view->nb[1]+size_t(b)*a.view->nb[2];
  if(offset+4>size)throw Refusal("input stride extent");a.bytes[offset/4]=input(k,row,b,y);
 }
 if(a.view->ne[0]!=K||a.view->ne[1]!=rows||a.view->ne[2]!=B||a.view->ne[3]!=1)throw Refusal("input shape");
 // Backend matrix helper stages only !dim01_contiguous, not merely a padded row pitch.
 if(layout && a.view->nb[1]==size_t(K)*a.view->nb[0] && a.view->nb[0]==sizeof(float))throw Refusal("noncontiguous control did not discriminate");
 return a;
}
struct Case {const char *name;int x,y;};
int main(int argc,char **argv){
 std::string device;bool corrupt=false;
 for(int i=1;i<argc;++i){const std::string arg=argv[i];if(arg=="--device"&&device.empty()&&i+1<argc)device=argv[++i];else if(arg=="--inject-corruption"&&!corrupt)corrupt=true;else{std::cout<<"{\"status\":\"NOT_CHECKED\",\"reason\":\"arguments\"}\n";return 2;}}
 if(device!="Vulkan0"&&device!="Vulkan1"){std::cout<<"{\"status\":\"NOT_CHECKED\",\"reason\":\"explicit device required\"}\n";return 2;}
 try{
  for(const char *flag:{"GGML_VK_DISABLE_F16","GGML_VK_DISABLE_FUSION","GGML_VK_DISABLE_COOPMAT","GGML_VK_DISABLE_COOPMAT2"}){const char *v=std::getenv(flag);if(!v||std::strcmp(v,"1"))throw Refusal("required child flag absent");}
  // Pinned static backend registry. No dynamic search/load-all, scheduler or CPU backend initialization.
  ggml_backend_dev_t dev=ggml_backend_dev_by_name(device.c_str());if(!dev)throw Refusal("selected device unavailable");
  auto reg=ggml_backend_dev_backend_reg(dev);const auto kind=ggml_backend_dev_type(dev);
  if(!reg||std::strcmp(ggml_backend_reg_name(reg),"Vulkan")||(kind!=GGML_BACKEND_DEVICE_TYPE_GPU&&kind!=GGML_BACKEND_DEVICE_TYPE_IGPU))throw Refusal("device is not Vulkan GPU/IGPU");
  Backend backend;backend.value=ggml_backend_dev_init(dev,nullptr);
  if(!backend.value||!ggml_backend_is_vk(backend.value)||ggml_backend_get_device(backend.value)!=dev)throw Refusal("backend ownership");
  const auto buft=ggml_backend_get_default_buffer_type(backend.value);
  if(!buft||ggml_backend_buft_get_device(buft)!=dev||!ggml_backend_dev_supports_buft(dev,buft))throw Refusal("buffer type ownership");
  const Case cases[]={{"contiguous",0,0},{"X_transpose",1,0},{"Y_stride",0,2},{"X_transpose_Y_stride",1,2},{"X_stride",2,0},{"Y_transpose",0,1},{"X_stride_Y_transpose",2,1}};
  bool passed=true;std::cout<<std::setprecision(17)<<"{\"scope\":\"F32_OPERATOR_ONLY_NOT_LLM_OR_CAPACITY\",\"device\":"<<quote(device.c_str())<<",\"description\":"<<quote(ggml_backend_dev_description(dev))<<",\"device_type\":"<<quote(kind==GGML_BACKEND_DEVICE_TYPE_IGPU?"IGPU_SHARED_NOT_DEDICATED":"GPU")<<",\"M\":32,\"N\":32,\"K\":64,\"batch\":2,\"atol\":"<<ATOL<<",\"rtol\":"<<RTOL<<",\"cases\":[";
  for(size_t ci=0;ci<sizeof(cases)/sizeof(cases[0]);++ci){
   Resources r;ggml_init_params params={2u<<20,nullptr,true};r.ctx=ggml_init(params);if(!r.ctx)throw Refusal("metadata allocation");
   Matrix x=matrix(r.ctx,M,cases[ci].x,false),y=matrix(r.ctx,N,cases[ci].y,true);ggml_tensor *z=ggml_mul_mat(r.ctx,x.view,y.view);
   if(!z||z->type!=GGML_TYPE_F32||z->ne[0]!=M||z->ne[1]!=N||z->ne[2]!=B||z->ne[3]!=1||!ggml_is_contiguous(z)||ggml_nbytes(z)>TENSOR_CAP)throw Refusal("output shape/type/extent");
   auto graph=ggml_new_graph_custom(r.ctx,32,false);if(!graph)throw Refusal("graph construction");ggml_build_forward_expand(graph,z);
   for(int node=0;node<ggml_graph_n_nodes(graph);++node)if(!ggml_backend_supports_op(backend.value,ggml_graph_node(graph,node)))throw Refusal("unsupported graph operation; CPU fallback forbidden");
   const size_t planned=ggml_backend_alloc_ctx_tensors_from_buft_size(r.ctx,buft);if(!planned||planned>TENSOR_CAP)throw Refusal("planned allocation cap");
   r.buffer=ggml_backend_alloc_ctx_tensors(r.ctx,backend.value);
   if(!r.buffer||ggml_backend_buffer_get_size(r.buffer)>TENSOR_CAP||ggml_backend_buft_get_device(ggml_backend_buffer_get_type(r.buffer))!=dev)throw Refusal("allocated buffer ownership/cap");
   for(auto t:{x.base,y.base,x.view,y.view,z})if(!t->buffer||ggml_backend_buft_get_device(ggml_backend_buffer_get_type(t->buffer))!=dev)throw Refusal("tensor buffer ownership");
   ggml_backend_tensor_set(x.base,x.bytes.data(),0,x.bytes.size()*4);ggml_backend_tensor_set(y.base,y.bytes.data(),0,y.bytes.size()*4);
   if(ggml_backend_graph_compute(backend.value,graph)!=GGML_STATUS_SUCCESS)throw std::runtime_error("GPU graph execution failed");ggml_backend_synchronize(backend.value);
   std::vector<float> actual(size_t(M)*N*B);ggml_backend_tensor_get(z,actual.data(),0,actual.size()*4);
   const bool injected=corrupt&&ci+1==sizeof(cases)/sizeof(cases[0]);if(injected)actual.back()+=8.0f;
   double max_abs=0,sum_sq=0;size_t failures=0,nonfinite=0;
   for(int b=0;b<B;++b)for(int n=0;n<N;++n)for(int m=0;m<M;++m){
    double expected=0;for(int k=0;k<K;++k)expected+=double(input(k,m,b,false))*double(input(k,n,b,true));
    const float value=actual[size_t(b)*M*N+size_t(n)*M+m];if(!std::isfinite(value)){++nonfinite;++failures;continue;}
    const double diff=std::abs(double(value)-expected);max_abs=std::max(max_abs,diff);sum_sq+=diff*diff;if(diff>ATOL+RTOL*std::abs(expected))++failures;
   }
   passed=passed&&!failures;if(ci)std::cout<<',';
   std::cout<<"{\"name\":"<<quote(cases[ci].name)<<",\"outputs\":"<<actual.size()<<",\"x_bytes\":"<<ggml_nbytes(x.base)<<",\"y_bytes\":"<<ggml_nbytes(y.base)<<",\"output_bytes\":"<<ggml_nbytes(z)<<",\"allocated_bytes\":"<<ggml_backend_buffer_get_size(r.buffer)<<",\"shape_checked\":true,\"buffer_owner_checked\":true,\"graph_status\":\"SUCCESS\",\"finite_count\":"<<actual.size()-nonfinite<<",\"fail_count\":"<<failures<<",\"max_abs\":"<<max_abs<<",\"rmse\":"<<std::sqrt(sum_sq/actual.size())<<",\"corruption_injected\":"<<(injected?"true":"false")<<'}';
  }
  std::cout<<"],\"status\":"<<quote(passed?"OPERATOR_PARITY_PASS":"OPERATOR_PARITY_FAIL")<<"}\n";return passed?0:1;
 }catch(const Refusal &e){std::cerr<<"NOT_CHECKED: "<<e.what()<<'\n';return 2;}catch(const std::exception &e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
}
