// Experimental CPU RPC pipeline; no GPU or VRAM qualification.
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include "ggml-rpc.h"
#include <cmath>
#include <cstdio>

struct Stage {
    ggml_backend_t backend = nullptr;
    ggml_context * context = nullptr;
    ggml_backend_buffer_t buffer = nullptr;
    ggml_tensor * weight = nullptr;
    ggml_tensor * input = nullptr;
    ggml_tensor * output = nullptr;
    ggml_cgraph * graph = nullptr;
    ~Stage() {
        if (buffer) ggml_backend_buffer_free(buffer);
        if (context) ggml_free(context);
        if (backend) ggml_backend_free(backend);
    }
};

int main(int argc, char ** argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: rpc_four_worker_smoke endpoint1 endpoint2 endpoint3 endpoint4\n");
        return 2;
    }
    Stage stages[4];
    float first_weight[]{1, 2, 3, 4}, input[]{5, 6, 7, 8}, scale[]{2, 0, 0, 2};
    const float expected[4][4]{{17,39,23,53},{34,78,46,106},{68,156,92,212},{136,312,184,424}};
    float actual[4]{};
    for (int i = 0; i < 4; ++i) {
        Stage & s = stages[i];
        s.backend = ggml_backend_rpc_init(argv[i+1], 0);
        if (!s.backend) { std::fprintf(stderr, "backend unavailable stage %d\n", i); return 3; }
        s.context = ggml_init({4*1024*1024, nullptr, true});
        if (!s.context) { std::fprintf(stderr, "context unavailable stage %d\n", i); return 4; }
        s.weight = ggml_new_tensor_2d(s.context, GGML_TYPE_F32, 2, 2);
        s.input = ggml_new_tensor_2d(s.context, GGML_TYPE_F32, 2, 2);
        if (!s.weight || !s.input) { std::fprintf(stderr, "tensor unavailable stage %d\n", i); return 5; }
        s.output = ggml_mul_mat(s.context, s.weight, s.input);
        s.graph = ggml_new_graph(s.context);
        if (!s.output || !s.graph) { std::fprintf(stderr, "graph unavailable stage %d\n", i); return 6; }
        ggml_build_forward_expand(s.graph, s.output);
        s.buffer = ggml_backend_alloc_ctx_tensors(s.context, s.backend);
        if (!s.buffer) { std::fprintf(stderr, "allocation unavailable stage %d\n", i); return 7; }
        ggml_backend_tensor_set(s.weight, i ? scale : first_weight, 0, sizeof(scale));
        if (!i) ggml_backend_tensor_set(s.input, input, 0, sizeof(input));
        else ggml_backend_tensor_copy(stages[i-1].output, s.input);
        if (ggml_backend_graph_compute(s.backend, s.graph) != GGML_STATUS_SUCCESS) {
            std::fprintf(stderr, "compute failed stage %d\n", i); return 8;
        }
        ggml_backend_synchronize(s.backend);
        ggml_backend_tensor_get(s.output, actual, 0, sizeof(actual));
        for (int j = 0; j < 4; ++j) {
            if (!std::isfinite(actual[j]) || std::fabs(actual[j]-expected[i][j]) >= 1e-5f) {
                std::fprintf(stderr, "parity failed stage %d element %d actual %g expected %g\n", i, j, actual[j], expected[i][j]);
                return 1;
            }
        }
    }
    std::printf("{\"status\":\"PASS\",\"qualification\":\"CPU_ONLY_NOT_GPU_QUALIFICATION\",\"workers\":4,\"computed_stages\":4,\"interworker_tensor_transfers\":3,\"values\":[%g,%g,%g,%g]}\n",
                actual[0],actual[1],actual[2],actual[3]);
    return 0;
}
