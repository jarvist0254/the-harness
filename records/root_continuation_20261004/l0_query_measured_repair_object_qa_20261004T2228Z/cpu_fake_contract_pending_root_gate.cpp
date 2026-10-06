// Independently authored CPU-only Level Zero stub contract.
// Not compiled or executed. LZQ_ACTUAL_SOURCE_PATH must point at the pinned candidate.
#include <ze_api.h>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <algorithm>
#include <cctype>

#ifndef LZQ_ACTUAL_SOURCE_PATH
#error LZQ_ACTUAL_SOURCE_PATH must identify the pinned candidate source
#endif
#define LZQ_TEST_NO_MAIN 1
#include LZQ_ACTUAL_SOURCE_PATH

enum CaseId {
    C_NORMAL, C_INIT_ERROR, C_DRIVER_COUNT_ERROR, C_DRIVER_COUNT_CHANGE,
    C_DEVICE_ERROR, C_DEVICE_COUNT_CHANGE, C_PROPERTIES_ERROR, C_EXTERNAL_ERROR,
    C_EXTERNAL_UNKNOWN, C_QUEUE_ERROR, C_QUEUE_UNKNOWN, C_PEER_UNKNOWN,
    C_P2P_ERROR, C_P2P_PROPS_ERROR, C_ZERO_DRIVERS, C_DRIVER_LIMIT, C_DEVICE_LIMIT,
    C_SUBDEVICE_LIMIT, C_ESCAPED_NAME, C_DUPLICATE_HANDLE_TWO_DRIVERS
};
static CaseId g_case = C_NORMAL;
static uint32_t g_driver_count = 1;
static uint32_t g_device_count = 1;
static uint32_t g_subdevice_count = 0;
static unsigned g_init_calls = 0, g_driver_calls = 0, g_device_calls = 0;
static unsigned g_property_calls = 0, g_ext_calls = 0, g_queue_calls = 0;
static unsigned g_peer_calls = 0, g_p2p_calls = 0;
static unsigned g_checks = 0, g_failures = 0;

static ze_driver_handle_t drv(unsigned i=0) { return reinterpret_cast<ze_driver_handle_t>(uintptr_t(0x100+i)); }
static ze_device_handle_t dev(unsigned i=0) { return reinterpret_cast<ze_device_handle_t>(uintptr_t(0x200+i)); }
static bool known(ze_device_handle_t h) { uintptr_t v=uintptr_t(h); return (v>=0x200 && v<0x200+LZQ_MAX_NODES)||(v>=0x1000 && v<0x1000+LZQ_MAX_SUBS); }
static void check(bool ok, const char*) { ++g_checks; if(!ok) ++g_failures; }

extern "C" ze_result_t ZE_APICALL zeInit(ze_init_flags_t flags) {
    ++g_init_calls;
    if(flags!=ZE_INIT_FLAG_GPU_ONLY) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    return g_case==C_INIT_ERROR ? ZE_RESULT_ERROR_DEVICE_LOST : ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDriverGet(uint32_t* count, ze_driver_handle_t* out) {
    ++g_driver_calls;
    if(!count) return ZE_RESULT_ERROR_INVALID_NULL_POINTER;
    if(g_case==C_DRIVER_COUNT_ERROR && !out) return ZE_RESULT_ERROR_DEVICE_LOST;
    if(g_case==C_ZERO_DRIVERS) g_driver_count=0;
    if(!out) { *count=g_driver_count; return ZE_RESULT_SUCCESS; }
    if(g_case==C_DRIVER_COUNT_CHANGE) { *count=*count+1; return ZE_RESULT_SUCCESS; }
    uint32_t n=std::min(*count,g_driver_count);
    for(uint32_t i=0;i<n;++i) out[i]=drv(i);
    *count=n;
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGet(ze_driver_handle_t driver, uint32_t* count, ze_device_handle_t* out) {
    ++g_device_calls;
    if(!count || uintptr_t(driver)<0x100 || uintptr_t(driver)>=0x100+LZQ_MAX_DRIVERS) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    if(g_case==C_DEVICE_ERROR && out) return ZE_RESULT_ERROR_DEVICE_LOST;
    if(g_case==C_DRIVER_LIMIT) g_driver_count=LZQ_MAX_DRIVERS+1;
    if(g_case==C_DEVICE_LIMIT) g_device_count=LZQ_MAX_NODES+1;
    if(g_case==C_DUPLICATE_HANDLE_TWO_DRIVERS) g_device_count=1;
    if(!out) { *count=g_device_count; return ZE_RESULT_SUCCESS; }
    if(g_case==C_DRIVER_COUNT_CHANGE || g_case==C_DEVICE_COUNT_CHANGE) { *count=*count+1; return ZE_RESULT_SUCCESS; }
    uint32_t n=std::min(*count,g_device_count);
    for(uint32_t i=0;i<n;++i) {
        if(g_case==C_DUPLICATE_HANDLE_TWO_DRIVERS) out[i]=dev(0);
        else out[i]=dev(i);
    }
    *count=n;
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetSubDevices(ze_device_handle_t h, uint32_t* count, ze_device_handle_t* out) {
    if(!known(h) || !count) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    if(g_case==C_SUBDEVICE_LIMIT) g_subdevice_count=LZQ_MAX_SUBS+1;
    if(!out) { *count=g_subdevice_count; return ZE_RESULT_SUCCESS; }
    uint32_t n=std::min(*count,g_subdevice_count);
    for(uint32_t i=0;i<n;++i) out[i]=reinterpret_cast<ze_device_handle_t>(uintptr_t(0x1000+i));
    *count=n;
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetProperties(ze_device_handle_t h, ze_device_properties_t* p) {
    ++g_property_calls;
    if(!known(h) || !p || p->stype!=ZE_STRUCTURE_TYPE_DEVICE_PROPERTIES || p->pNext) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    if(g_case==C_PROPERTIES_ERROR) return ZE_RESULT_ERROR_DEVICE_LOST;
    unsigned i=uintptr_t(h)>=0x1000 ? unsigned(uintptr_t(h)-0x1000+LZQ_MAX_NODES) : unsigned(uintptr_t(h)-0x200);
    p->type=ZE_DEVICE_TYPE_GPU; p->vendorId=0x8086; p->deviceId=0x1000+i; p->subdeviceId=0;
    for(unsigned j=0;j<16;++j) p->uuid.id[j]=uint8_t(i*17+j);
    std::memset(p->name,0,sizeof(p->name));
    if(g_case==C_ESCAPED_NAME) { p->name[0]='"'; p->name[1]='\\'; p->name[2]=1; p->name[3]='x'; }
    else std::snprintf(p->name,sizeof(p->name),"CPU_FAKE_%u",i);
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetExternalMemoryProperties(ze_device_handle_t h, ze_device_external_memory_properties_t* p) {
    ++g_ext_calls;
    if(!known(h) || !p || p->stype!=ZE_STRUCTURE_TYPE_DEVICE_EXTERNAL_MEMORY_PROPERTIES || p->pNext) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    if(g_case==C_EXTERNAL_ERROR) return ZE_RESULT_ERROR_DEVICE_LOST;
    if(g_case==C_EXTERNAL_UNKNOWN) return ZE_RESULT_ERROR_UNSUPPORTED_FEATURE;
    if(g_case==C_PROPERTIES_ERROR) return ZE_RESULT_ERROR_DEVICE_LOST;
    p->memoryAllocationImportTypes=ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF;
    p->memoryAllocationExportTypes=ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF;
    p->imageImportTypes=0; p->imageExportTypes=0;
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetCommandQueueGroupProperties(ze_device_handle_t h, uint32_t* count, ze_command_queue_group_properties_t* p) {
    ++g_queue_calls;
    if(!known(h) || !count) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    if(g_case==C_QUEUE_ERROR) return ZE_RESULT_ERROR_DEVICE_LOST;
    if(g_case==C_QUEUE_UNKNOWN) return ZE_RESULT_ERROR_UNSUPPORTED_FEATURE;
    if(!p) { *count=1; return ZE_RESULT_SUCCESS; }
    if(*count) { p[0].flags=ZE_COMMAND_QUEUE_GROUP_PROPERTY_FLAG_COMPUTE; p[0].numQueues=1; *count=1; }
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceCanAccessPeer(ze_device_handle_t a, ze_device_handle_t b, ze_bool_t* out) {
    ++g_peer_calls;
    if(!known(a)||!known(b)||!out) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    if(g_case==C_PEER_UNKNOWN) return ZE_RESULT_ERROR_UNSUPPORTED_FEATURE;
    if(g_case==C_P2P_ERROR) return ZE_RESULT_ERROR_DEVICE_LOST;
    *out=1;
    return ZE_RESULT_SUCCESS;
}
extern "C" ze_result_t ZE_APICALL zeDeviceGetP2PProperties(ze_device_handle_t a, ze_device_handle_t b, ze_device_p2p_properties_t* p) {
    ++g_p2p_calls;
    if(!known(a)||!known(b)||!p||p->stype!=ZE_STRUCTURE_TYPE_DEVICE_P2P_PROPERTIES||p->pNext) return ZE_RESULT_ERROR_INVALID_ARGUMENT;
    if(g_case==C_P2P_PROPS_ERROR) return ZE_RESULT_ERROR_DEVICE_LOST;
    p->flags=ZE_DEVICE_P2P_PROPERTY_FLAG_ACCESS;
    return ZE_RESULT_SUCCESS;
}

struct JsonCheck {
    const char* p; const char* end;
    void ws(){ while(p<end && (*p==' '||*p=='\t'||*p=='\r'||*p=='\n')) ++p; }
    bool string(){ if(p==end||*p++!='"') return false; while(p<end){ unsigned char c=(unsigned char)*p++; if(c=='"') return true; if(c<0x20) return false; if(c=='\\'){ if(p==end) return false; char e=*p++; if(e=='u'){ for(int i=0;i<4;++i){ if(p==end||!std::isxdigit((unsigned char)*p++)) return false; } } else if(!std::strchr("\"\\/bfnrt",e)) return false; } } return false; }
    bool value(unsigned d=0){ if(d>64) return false; ws(); if(p==end) return false; if(*p=='"') return string(); if(*p=='{'||*p=='['){ char close=*p++=='{'?'}':']'; ws(); if(p<end&&*p==close){++p;return true;} for(;;){ if(close=='}'){ ws(); if(!string()) return false; ws(); if(p==end||*p++!=':') return false; } if(!value(d+1)) return false; ws(); if(p==end) return false; if(*p==close){++p;return true;} if(*p++!=',') return false; } } if(*p=='t'&&end-p>=4&&std::memcmp(p,"true",4)==0){p+=4;return true;} if(*p=='f'&&end-p>=5&&std::memcmp(p,"false",5)==0){p+=5;return true;} if(*p=='n'&&end-p>=4&&std::memcmp(p,"null",4)==0){p+=4;return true;} if(*p=='-') ++p; if(p==end||*p<'0'||*p>'9') return false; if(*p=='0') ++p; else while(p<end&&*p>='0'&&*p<='9') ++p; if(p<end&&*p=='.'){++p;if(p==end||*p<'0'||*p>'9')return false;while(p<end&&*p>='0'&&*p<='9')++p;} if(p<end&&(*p=='e'||*p=='E')){++p;if(p<end&&(*p=='+'||*p=='-'))++p;if(p==end||*p<'0'||*p>'9')return false;while(p<end&&*p>='0'&&*p<='9')++p;} return true; }
    bool whole(){ ws(); if(!value()) return false; ws(); return p==end; }
};
static bool json_valid(const char* b,size_t n){ JsonCheck j{b,b+n}; return j.whole(); }
static bool has(const char* b,const char* s){ return std::strstr(b,s)!=nullptr; }
static size_t collect(CaseId c, char* out, size_t cap){ g_case=c; g_driver_count=c==C_DUPLICATE_HANDLE_TWO_DRIVERS?2:1; g_device_count=(c==C_PEER_UNKNOWN||c==C_P2P_ERROR||c==C_P2P_PROPS_ERROR)?2:1; g_subdevice_count=0; g_init_calls=g_driver_calls=g_device_calls=g_property_calls=g_ext_calls=g_queue_calls=g_peer_calls=g_p2p_calls=0; std::memset(out,0,cap+1); return lzq_collect(out,cap); }
static void test_normal_reports_capability_not_transport(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_NORMAL,b,LZQ_OUT_BYTES); check(json_valid(b,n),"normal JSON parses"); b[n]=0; check(lzq_exit==0&&has(b,"\"status\":\"PASS\""),"normal query status"); check(has(b,"\"direct_transport_qualified\":false"),"no transport qualification"); }
static void test_failure_codes_are_structured(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_INIT_ERROR,b,LZQ_OUT_BYTES); check(json_valid(b,n),"init error JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"zeInit\""),"init error stage/exit"); n=collect(C_DRIVER_COUNT_ERROR,b,LZQ_OUT_BYTES); check(json_valid(b,n),"driver error JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"zeDriverGet_count\""),"driver count error stage/exit"); }
static void test_zero_drivers_are_not_checked_not_pass(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_ZERO_DRIVERS,b,LZQ_OUT_BYTES); check(json_valid(b,n),"zero driver JSON parses"); b[n]=0; check(lzq_exit==2&&has(b,"\"status\":\"NOT_CHECKED\""),"no drivers stays NOT_CHECKED"); }
static void test_unknown_capabilities_remain_unknown(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_EXTERNAL_UNKNOWN,b,LZQ_OUT_BYTES); check(json_valid(b,n),"external unknown JSON parses"); b[n]=0; check(lzq_exit==0&&has(b,"\"state\":\"unknown\""),"unsupported external property stays unknown"); n=collect(C_QUEUE_UNKNOWN,b,LZQ_OUT_BYTES); check(json_valid(b,n),"queue unknown JSON parses"); b[n]=0; check(lzq_exit==0&&has(b,"\"queue_groups_state\":\"unknown\""),"unsupported queue query stays unknown"); n=collect(C_PEER_UNKNOWN,b,LZQ_OUT_BYTES); check(json_valid(b,n),"peer unknown JSON parses"); b[n]=0; check(lzq_exit==0&&has(b,"\"can_access\":null"),"unsupported peer query stays null"); }
static void test_error_during_property_collection_is_not_pass(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_PROPERTIES_ERROR,b,LZQ_OUT_BYTES); check(json_valid(b,n),"property error JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"status\":\"FAIL\""),"property error cannot pass"); }
static void test_capability_query_errors_are_not_pass(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_EXTERNAL_ERROR,b,LZQ_OUT_BYTES); check(json_valid(b,n),"external error JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"root_row\""),"external query error cannot pass"); n=collect(C_QUEUE_ERROR,b,LZQ_OUT_BYTES); check(json_valid(b,n),"queue error JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"root_row\""),"queue query error cannot pass"); }
static void test_peer_query_errors_are_not_pass(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_P2P_ERROR,b,LZQ_OUT_BYTES); check(json_valid(b,n),"peer query error JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"zeDeviceCanAccessPeer\""),"peer query error cannot pass"); n=collect(C_P2P_PROPS_ERROR,b,LZQ_OUT_BYTES); check(json_valid(b,n),"peer properties error JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"zeDeviceGetP2PProperties\""),"peer properties error cannot pass"); }
static void test_count_growth_during_fill_is_refused(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_DRIVER_COUNT_CHANGE,b,LZQ_OUT_BYTES); check(json_valid(b,n),"changed driver count JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"zeDriverGet_handles\""),"count/list inconsistency refused"); }
static void test_device_count_growth_during_fill_is_refused(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_DEVICE_COUNT_CHANGE,b,LZQ_OUT_BYTES); check(json_valid(b,n),"changed device count JSON parses"); b[n]=0; check(lzq_exit==1&&has(b,"\"stage\":\"zeDeviceGet_handles\""),"device count/list inconsistency refused"); }
static void test_escaped_device_names_keep_json_valid(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_ESCAPED_NAME,b,LZQ_OUT_BYTES); check(json_valid(b,n),"escaped name JSON parses"); b[n]=0; check(lzq_exit==0&&has(b,"\\\""),"name escaping retained"); }
static void test_subdevice_cap_is_disclosed(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_SUBDEVICE_LIMIT,b,LZQ_OUT_BYTES); check(json_valid(b,n),"subdevice-limited JSON parses"); b[n]=0; check(has(b,"\"inventory_truncated\":true"),"subdevice cap is disclosed"); check(has(b,"\"subdevice_nodes\":64"),"bounded subdevice count is explicit"); }
static void test_duplicate_handle_from_second_driver_is_alias_not_new_root(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_DUPLICATE_HANDLE_TWO_DRIVERS,b,LZQ_OUT_BYTES); check(json_valid(b,n),"aliased-root JSON parses"); b[n]=0; check(has(b,"\"physical_root_devices\":1"),"same handle remains one root"); check(has(b,"\"enumerated_root_rows\":2"),"both driver rows remain represented"); check(has(b,"\"alias_count\":2"),"alias count is explicit"); }
static void test_device_limit_is_explicitly_truncated(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_DEVICE_LIMIT,b,LZQ_OUT_BYTES); check(json_valid(b,n),"bounded inventory JSON parses"); b[n]=0; check(has(b,"\"inventory_truncated\":true"),"root cap is disclosed"); check(has(b,"\"direct_transport_qualified\":false"),"truncated result still not transport"); }
static void test_driver_limit_is_explicitly_truncated(){ char b[LZQ_OUT_BYTES+1]; size_t n=collect(C_DRIVER_LIMIT,b,LZQ_OUT_BYTES); check(json_valid(b,n),"driver-limited JSON parses"); b[n]=0; check(has(b,"\"drivers\":32"),"driver cap is explicit"); check(has(b,"\"inventory_truncated\":true"),"driver cap is disclosed"); }
static void test_small_output_capacity_cannot_be_accepted_as_complete_pass(){ char b[65]; size_t n=collect(C_NORMAL,b,64); b[n]=0; bool complete=json_valid(b,n); check(lzq_exit!=0 || complete,"small-buffer output must not pair partial JSON with success exit"); }
int main(){
    test_normal_reports_capability_not_transport();
    test_failure_codes_are_structured();
    test_zero_drivers_are_not_checked_not_pass();
    test_unknown_capabilities_remain_unknown();
    test_error_during_property_collection_is_not_pass();
    test_capability_query_errors_are_not_pass();
    test_peer_query_errors_are_not_pass();
    test_count_growth_during_fill_is_refused();
    test_device_count_growth_during_fill_is_refused();
    test_escaped_device_names_keep_json_valid();
    test_subdevice_cap_is_disclosed();
    test_duplicate_handle_from_second_driver_is_alias_not_new_root();
    test_device_limit_is_explicitly_truncated();
    test_driver_limit_is_explicitly_truncated();
    test_small_output_capacity_cannot_be_accepted_as_complete_pass();
    std::printf("cpu_fake_checks=%u failures=%u\n",g_checks,g_failures);
    return g_failures?1:0;
}
