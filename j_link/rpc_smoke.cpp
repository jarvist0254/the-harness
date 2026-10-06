// Real ggml RPC tensor execution smoke test. CPU workers are not GPU qualification.
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include "ggml-rpc.h"
#include <cmath>
#include <cstdio>

int main(int argc, char **argv) {
    if (argc != 3) { std::fprintf(stderr, "usage: rpc_smoke endpoint1 endpoint2\n"); return 2; }
    auto backend1 = ggml_backend_rpc_init(argv[1], 0);
    auto backend2 = ggml_backend_rpc_init(argv[2], 0);
    if (!backend1 || !backend2) { std::fprintf(stderr, "RPC backend unavailable\n"); return 3; }
    ggml_init_params params{4*1024*1024, nullptr, true};
    auto ctx1 = ggml_init(params);
    auto ctx2 = ggml_init(params);
    auto a = ggml_new_tensor_2d(ctx1, GGML_TYPE_F32, 2, 2);
    auto x = ggml_new_tensor_2d(ctx1, GGML_TYPE_F32, 2, 2);
    auto y = ggml_mul_mat(ctx1, a, x);
    auto g1 = ggml_new_graph(ctx1);
    ggml_build_forward_expand(g1, y);
    auto buffer1 = ggml_backend_alloc_ctx_tensors(ctx1, backend1);
    auto w = ggml_new_tensor_2d(ctx2, GGML_TYPE_F32, 2, 2);
    auto input2 = ggml_new_tensor_2d(ctx2, GGML_TYPE_F32, 2, 2);
    auto output = ggml_mul_mat(ctx2, w, input2);
    auto g2 = ggml_new_graph(ctx2);
    ggml_build_forward_expand(g2, output);
    auto buffer2 = ggml_backend_alloc_ctx_tensors(ctx2, backend2);
    if (!buffer1 || !buffer2) { std::fprintf(stderr, "Allocation failed\n"); return 4; }
    float av[]{1,2,3,4}, xv[]{5,6,7,8}, wv[]{2,0,0,2};
    ggml_backend_tensor_set(a,av,0,sizeof(av));
    ggml_backend_tensor_set(x,xv,0,sizeof(xv));
    ggml_backend_tensor_set(w,wv,0,sizeof(wv));
    auto s1 = ggml_backend_graph_compute(backend1,g1);
    if (s1 != GGML_STATUS_SUCCESS) { std::fprintf(stderr,"Stage 1 failed\n"); return 5; }
    ggml_backend_synchronize(backend1);
    ggml_backend_tensor_copy(y,input2);
    auto s2 = ggml_backend_graph_compute(backend2,g2);
    if (s2 != GGML_STATUS_SUCCESS) { std::fprintf(stderr,"Stage 2 failed\n"); return 6; }
    ggml_backend_synchronize(backend2);
    float actual[4], expected[]{34,78,46,106};
    ggml_backend_tensor_get(output,actual,0,sizeof(actual));
    bool pass = true;
    for (int i=0;i<4;i++) pass = pass && std::isfinite(actual[i]) && std::fabs(actual[i]-expected[i])<1e-5;
    std::printf("{\"test\":\"two_worker_rpc_tensor_pipeline\",\"pass\":%s,\"values\":[%g,%g,%g,%g],\"gpu_qualified\":false}\n",
        pass ? "true":"false",actual[0],actual[1],actual[2],actual[3]);
    ggml_backend_buffer_free(buffer2); ggml_backend_buffer_free(buffer1);
    ggml_free(ctx2); ggml_free(ctx1);
    ggml_backend_free(backend2); ggml_backend_free(backend1);
    return pass ? 0 : 1;
}
