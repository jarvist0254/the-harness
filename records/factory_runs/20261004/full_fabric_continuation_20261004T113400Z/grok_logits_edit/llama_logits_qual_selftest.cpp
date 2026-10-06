#define LLAMA_LOGITS_QUAL_NO_MAIN
#include "llama_logits_qual.cpp"
#ifdef _WIN32
int main(){return qual_self_test();}
#else
int main(){fputs("{\"status\":\"ERROR\",\"exit_code\":2,\"error\":\"NOT_CHECKED\"}\n",stdout);return 2;}
#endif

