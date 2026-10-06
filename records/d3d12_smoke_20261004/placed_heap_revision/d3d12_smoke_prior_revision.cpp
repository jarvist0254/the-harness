#include <windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <wrl/client.h>
#include <vector>
#include <string>
#include <iostream>
#include <iomanip>
#include <cstdint>

using Microsoft::WRL::ComPtr;

static UINT gProducerVendorId = 0;
static UINT gConsumerVendorId = 0;
static D3D12_HEAP_PROPERTIES gReturnedHeapProperties = {};
static D3D12_HEAP_FLAGS gReturnedHeapFlags = static_cast<D3D12_HEAP_FLAGS>(0);
static bool gReturnedHeapPropertiesKnown = false;

struct HandleCloser {
    void operator()(HANDLE h) const { if (h && h != INVALID_HANDLE_VALUE) CloseHandle(h); }
};
using UniqueHandle = std::unique_ptr<void, HandleCloser>;

struct AdapterInfo {
    ComPtr<IDXGIAdapter1> adapter;
    LUID luid;
    DXGI_ADAPTER_DESC1 desc;
};

static std::string EscapeJson(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 8);
    for (char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default: out += c; break;
        }
    }
    return out;
}

static void PrintJson(const std::string& status, const std::string& reason,
                      const LUID* prodLuid = nullptr, const LUID* consLuid = nullptr,
                      uint64_t prodDedicated = 0, uint64_t prodShared = 0,
                      uint64_t consDedicated = 0, uint64_t consShared = 0,
                      uint64_t bytesChecked = 0, const std::string& transport = "",
                      int64_t mismatchOffset = -1, HRESULT hr = S_OK) {
    std::cout << "{\"status\":\"" << EscapeJson(status) << "\",\"reason\":\"" << EscapeJson(reason) << "\"";
    if (prodLuid) {
        std::cout << ",\"producerLUID\":\"0x" << std::hex << std::setw(8) << std::setfill('0') << prodLuid->HighPart
                  << std::setw(8) << std::setfill('0') << prodLuid->LowPart << std::dec << "\"";
    }
    if (consLuid) {
        std::cout << ",\"consumerLUID\":\"0x" << std::hex << std::setw(8) << std::setfill('0') << consLuid->HighPart
                  << std::setw(8) << std::setfill('0') << consLuid->LowPart << std::dec << "\"";
    }
    if (prodLuid || consLuid) {
        std::cout << ",\"producerVendorId\":\"0x" << std::hex << std::setw(4) << std::setfill('0') << gProducerVendorId
                  << "\",\"consumerVendorId\":\"0x" << std::setw(4) << std::setfill('0') << gConsumerVendorId << std::dec << "\"";
        std::cout << ",\"producerDedicatedMB\":" << (prodDedicated / (1024 * 1024))
                  << ",\"producerSharedMB\":" << (prodShared / (1024 * 1024))
                  << ",\"consumerDedicatedMB\":" << (consDedicated / (1024 * 1024))
                  << ",\"consumerSharedMB\":" << (consShared / (1024 * 1024));
    }
    std::cout << ",\"memory_placement_class\":\"SPEC_REQUIRED_L0_SYSTEM_MEMORY_NOT_RESIDENCY_MEASURED\""
              << ",\"requested_heap_type\":\"DEFAULT\""
              << ",\"requested_cpu_page_property\":\"UNKNOWN\""
              << ",\"requested_memory_pool_preference\":\"UNKNOWN\""
              << ",\"requested_heap_flags\":"
              << static_cast<uint32_t>(D3D12_HEAP_FLAG_SHARED | D3D12_HEAP_FLAG_SHARED_CROSS_ADAPTER);
    if (gReturnedHeapPropertiesKnown) {
        std::cout << ",\"returned_heap_type\":" << static_cast<int>(gReturnedHeapProperties.Type)
                  << ",\"returned_cpu_page_property\":" << static_cast<int>(gReturnedHeapProperties.CPUPageProperty)
                  << ",\"returned_memory_pool_preference\":" << static_cast<int>(gReturnedHeapProperties.MemoryPoolPreference)
                  << ",\"returned_creation_node_mask\":" << gReturnedHeapProperties.CreationNodeMask
                  << ",\"returned_visible_node_mask\":" << gReturnedHeapProperties.VisibleNodeMask
                  << ",\"returned_heap_flags\":" << static_cast<uint32_t>(gReturnedHeapFlags);
    }
    if (!transport.empty()) std::cout << ",\"transport\":\"" << EscapeJson(transport) << "\"";
    if (bytesChecked > 0) std::cout << ",\"bytes_checked\":" << bytesChecked;
    if (mismatchOffset >= 0) std::cout << ",\"mismatch_offset\":" << mismatchOffset;
    std::cout << ",\"hr\":" << hr << ",\"hr_hex\":\"0x" << std::hex << std::setw(8) << std::setfill('0')
              << static_cast<uint32_t>(hr) << std::dec << "\"}" << std::endl;
}

int main(int argc, char** argv) {
    bool injectCorruption = false;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--inject-corruption") injectCorruption = true;
    }

    const UINT64 kBufferSize = 256 * 1024;
    const std::string kTransport = "SPEC_REQUIRED_L0_SYSTEM_MEMORY_NOT_RESIDENCY_MEASURED";

    // 1. Enumerate physical adapters
    ComPtr<IDXGIFactory4> factory;
    HRESULT hr = CreateDXGIFactory1(IID_PPV_ARGS(&factory));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateDXGIFactory1 failed", nullptr, nullptr, 0, 0, 0, 0, 0, "", -1, hr);
        return 1;
    }

    std::vector<AdapterInfo> adapters;
    for (UINT i = 0; ; ++i) {
        ComPtr<IDXGIAdapter1> adapter;
        hr = factory->EnumAdapters1(i, &adapter);
        if (hr == DXGI_ERROR_NOT_FOUND) break;
        if (FAILED(hr)) continue;

        DXGI_ADAPTER_DESC1 desc = {};
        hr = adapter->GetDesc1(&desc);
        if (FAILED(hr)) continue;
        if (desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) continue;

        ComPtr<ID3D12Device> testDevice;
        hr = D3D12CreateDevice(adapter.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&testDevice));
        if (SUCCEEDED(hr)) {
            AdapterInfo info;
            info.adapter = adapter;
            info.luid = desc.AdapterLuid;
            info.desc = desc;
            adapters.push_back(info);
        }
    }

    if (adapters.size() < 2) {
        PrintJson("UNSUPPORTED", "Fewer than 2 physical D3D12-capable adapters found");
        return 0;
    }

    // Require real NVIDIA and AMD hardware adapters; never fall back to WARP/software.
    AdapterInfo* prodInfo = nullptr;
    AdapterInfo* consInfo = nullptr;
    for (size_t i = 0; i < adapters.size() && !consInfo; ++i) {
        if (adapters[i].desc.VendorId != 0x10DE) continue;
        for (size_t j = 0; j < adapters.size(); ++j) {
            if (adapters[j].desc.VendorId == 0x1002 &&
                (adapters[i].luid.HighPart != adapters[j].luid.HighPart ||
                 adapters[i].luid.LowPart != adapters[j].luid.LowPart)) {
                prodInfo = &adapters[i];
                consInfo = &adapters[j];
                break;
            }
        }
    }
    if (!consInfo) {
        PrintJson("UNSUPPORTED", "Required NVIDIA (vendor 0x10DE) and AMD (vendor 0x1002) hardware adapters unavailable");
        return 0;
    }
    gProducerVendorId = prodInfo->desc.VendorId;
    gConsumerVendorId = consInfo->desc.VendorId;

    // 2. Create devices and copy queues
    ComPtr<ID3D12Device> prodDevice;
    ComPtr<ID3D12Device> consDevice;
    hr = D3D12CreateDevice(prodInfo->adapter.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&prodDevice));
    if (FAILED(hr)) {
        PrintJson("FAIL", "D3D12CreateDevice producer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }
    hr = D3D12CreateDevice(consInfo->adapter.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&consDevice));
    if (FAILED(hr)) {
        PrintJson("FAIL", "D3D12CreateDevice consumer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    D3D12_COMMAND_QUEUE_DESC queueDesc = {};
    queueDesc.Type = D3D12_COMMAND_LIST_TYPE_COPY;
    queueDesc.Flags = D3D12_COMMAND_QUEUE_FLAG_NONE;

    ComPtr<ID3D12CommandQueue> prodQueue;
    ComPtr<ID3D12CommandQueue> consQueue;
    hr = prodDevice->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&prodQueue));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommandQueue producer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }
    hr = consDevice->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&consQueue));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommandQueue consumer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    // 3. Create shared cross-adapter buffer on producer
    D3D12_HEAP_PROPERTIES heapProps = {};
    heapProps.Type = D3D12_HEAP_TYPE_DEFAULT;
    heapProps.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    heapProps.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;
    heapProps.CreationNodeMask = 1;
    heapProps.VisibleNodeMask = 1;

    D3D12_RESOURCE_DESC resourceDesc = {};
    resourceDesc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
    resourceDesc.Alignment = 0;
    resourceDesc.Width = kBufferSize;
    resourceDesc.Height = 1;
    resourceDesc.DepthOrArraySize = 1;
    resourceDesc.MipLevels = 1;
    resourceDesc.Format = DXGI_FORMAT_UNKNOWN;
    resourceDesc.SampleDesc.Count = 1;
    resourceDesc.SampleDesc.Quality = 0;
    resourceDesc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    resourceDesc.Flags = D3D12_RESOURCE_FLAG_ALLOW_CROSS_ADAPTER;

    ComPtr<ID3D12Resource> prodSharedBuffer;
    hr = prodDevice->CreateCommittedResource(
        &heapProps,
        D3D12_HEAP_FLAG_SHARED | D3D12_HEAP_FLAG_SHARED_CROSS_ADAPTER,
        &resourceDesc,
        D3D12_RESOURCE_STATE_COMMON,
        nullptr,
        IID_PPV_ARGS(&prodSharedBuffer));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommittedResource SHARED|SHARED_CROSS_ADAPTER failed",
                  &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }
    hr = prodSharedBuffer->GetHeapProperties(&gReturnedHeapProperties, &gReturnedHeapFlags);
    if (FAILED(hr)) {
        PrintJson("FAIL", "GetHeapProperties on shared cross-adapter resource failed",
                  &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }
    gReturnedHeapPropertiesKnown = true;

    // 4. Create shared fence on producer
    ComPtr<ID3D12Fence> prodFence;
    hr = prodDevice->CreateFence(0, D3D12_FENCE_FLAG_SHARED | D3D12_FENCE_FLAG_SHARED_CROSS_ADAPTER,
                                 IID_PPV_ARGS(&prodFence));
    if (FAILED(hr)) {
        PrintJson("UNSUPPORTED", "CreateFence SHARED|SHARED_CROSS_ADAPTER failed",
                  &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 0;
    }

    // 5. Share buffer handle
    UniqueHandle hSharedBuffer(CreateEvent(nullptr, TRUE, FALSE, nullptr));
    HANDLE rawBufferHandle = nullptr;
    hr = prodDevice->CreateSharedHandle(prodSharedBuffer.Get(), nullptr, GENERIC_ALL, nullptr, &rawBufferHandle);
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateSharedHandle buffer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }
    UniqueHandle hBuffer(rawBufferHandle);

    // 6. Share fence handle
    HANDLE rawFenceHandle = nullptr;
    hr = prodDevice->CreateSharedHandle(prodFence.Get(), nullptr, GENERIC_ALL, nullptr, &rawFenceHandle);
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateSharedHandle fence failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }
    UniqueHandle hFence(rawFenceHandle);

    // 7. Open shared buffer on consumer
    ComPtr<ID3D12Resource> consSharedBuffer;
    hr = consDevice->OpenSharedHandle(hBuffer.get(), IID_PPV_ARGS(&consSharedBuffer));
    if (FAILED(hr)) {
        PrintJson("UNSUPPORTED", "OpenSharedHandle buffer on consumer failed",
                  &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 0;
    }

    // 8. Open shared fence on consumer
    ComPtr<ID3D12Fence> consSharedFence;
    hr = consDevice->OpenSharedHandle(hFence.get(), IID_PPV_ARGS(&consSharedFence));
    if (FAILED(hr)) {
        PrintJson("UNSUPPORTED", "OpenSharedHandle fence on consumer failed",
                  &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 0;
    }

    // 9. Producer upload buffer
    D3D12_HEAP_PROPERTIES uploadHeapProps = {};
    uploadHeapProps.Type = D3D12_HEAP_TYPE_UPLOAD;
    uploadHeapProps.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    uploadHeapProps.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;
    uploadHeapProps.CreationNodeMask = 1;
    uploadHeapProps.VisibleNodeMask = 1;

    D3D12_RESOURCE_DESC uploadDesc = resourceDesc;
    uploadDesc.Flags = D3D12_RESOURCE_FLAG_NONE;

    ComPtr<ID3D12Resource> prodUploadBuffer;
    hr = prodDevice->CreateCommittedResource(&uploadHeapProps, D3D12_HEAP_FLAG_NONE, &uploadDesc,
                                             D3D12_RESOURCE_STATE_GENERIC_READ, nullptr,
                                             IID_PPV_ARGS(&prodUploadBuffer));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommittedResource upload failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    BYTE* pUploadData = nullptr;
    hr = prodUploadBuffer->Map(0, nullptr, reinterpret_cast<void**>(&pUploadData));
    if (FAILED(hr)) {
        PrintJson("FAIL", "Map upload buffer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }
    for (UINT64 i = 0; i < kBufferSize; ++i) {
        pUploadData[i] = static_cast<BYTE>((i * 7 + 13) % 256);
    }
    if (injectCorruption) {
        pUploadData[12345] ^= 0xFF;
    }
    prodUploadBuffer->Unmap(0, nullptr);

    // 10. Producer command list: transition to COPY_DEST, copy, transition to COMMON
    ComPtr<ID3D12CommandAllocator> prodCmdAlloc;
    hr = prodDevice->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY, IID_PPV_ARGS(&prodCmdAlloc));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommandAllocator producer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    ComPtr<ID3D12GraphicsCommandList> prodCmdList;
    hr = prodDevice->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_COPY, prodCmdAlloc.Get(), nullptr,
                                       IID_PPV_ARGS(&prodCmdList));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommandList producer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    D3D12_RESOURCE_BARRIER toCopyDest = {};
    toCopyDest.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    toCopyDest.Transition.pResource = prodSharedBuffer.Get();
    toCopyDest.Transition.StateBefore = D3D12_RESOURCE_STATE_COMMON;
    toCopyDest.Transition.StateAfter = D3D12_RESOURCE_STATE_COPY_DEST;
    toCopyDest.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;

    D3D12_RESOURCE_BARRIER toCommon = {};
    toCommon.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    toCommon.Transition.pResource = prodSharedBuffer.Get();
    toCommon.Transition.StateBefore = D3D12_RESOURCE_STATE_COPY_DEST;
    toCommon.Transition.StateAfter = D3D12_RESOURCE_STATE_COMMON;
    toCommon.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;

    prodCmdList->ResourceBarrier(1, &toCopyDest);
    prodCmdList->CopyResource(prodSharedBuffer.Get(), prodUploadBuffer.Get());
    prodCmdList->ResourceBarrier(1, &toCommon);
    hr = prodCmdList->Close();
    if (FAILED(hr)) {
        PrintJson("FAIL", "Close producer command list failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    ID3D12CommandList* prodLists[] = { prodCmdList.Get() };
    prodQueue->ExecuteCommandLists(1, prodLists);

    const UINT64 kFenceValue = 1;
    hr = prodQueue->Signal(prodFence.Get(), kFenceValue);
    if (FAILED(hr)) {
        PrintJson("FAIL", "Signal producer fence failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    // 11. Consumer waits on shared fence via queue Wait
    hr = consQueue->Wait(consSharedFence.Get(), kFenceValue);
    if (FAILED(hr)) {
        PrintJson("FAIL", "Consumer queue Wait on shared fence failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    // 12. Consumer readback buffer
    D3D12_HEAP_PROPERTIES readbackHeapProps = {};
    readbackHeapProps.Type = D3D12_HEAP_TYPE_READBACK;
    readbackHeapProps.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    readbackHeapProps.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;
    readbackHeapProps.CreationNodeMask = 1;
    readbackHeapProps.VisibleNodeMask = 1;

    D3D12_RESOURCE_DESC readbackDesc = resourceDesc;
    readbackDesc.Flags = D3D12_RESOURCE_FLAG_NONE;

    ComPtr<ID3D12Resource> consReadbackBuffer;
    hr = consDevice->CreateCommittedResource(&readbackHeapProps, D3D12_HEAP_FLAG_NONE, &readbackDesc,
                                             D3D12_RESOURCE_STATE_COPY_DEST, nullptr,
                                             IID_PPV_ARGS(&consReadbackBuffer));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommittedResource readback failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    // 13. Consumer command list: transition shared to COPY_SOURCE, copy, transition back to COMMON
    ComPtr<ID3D12CommandAllocator> consCmdAlloc;
    hr = consDevice->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY, IID_PPV_ARGS(&consCmdAlloc));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommandAllocator consumer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    ComPtr<ID3D12GraphicsCommandList> consCmdList;
    hr = consDevice->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_COPY, consCmdAlloc.Get(), nullptr,
                                       IID_PPV_ARGS(&consCmdList));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateCommandList consumer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    D3D12_RESOURCE_BARRIER toCopySource = {};
    toCopySource.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    toCopySource.Transition.pResource = consSharedBuffer.Get();
    toCopySource.Transition.StateBefore = D3D12_RESOURCE_STATE_COMMON;
    toCopySource.Transition.StateAfter = D3D12_RESOURCE_STATE_COPY_SOURCE;
    toCopySource.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;

    D3D12_RESOURCE_BARRIER backToCommon = {};
    backToCommon.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    backToCommon.Transition.pResource = consSharedBuffer.Get();
    backToCommon.Transition.StateBefore = D3D12_RESOURCE_STATE_COPY_SOURCE;
    backToCommon.Transition.StateAfter = D3D12_RESOURCE_STATE_COMMON;
    backToCommon.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;

    consCmdList->ResourceBarrier(1, &toCopySource);
    consCmdList->CopyResource(consReadbackBuffer.Get(), consSharedBuffer.Get());
    consCmdList->ResourceBarrier(1, &backToCommon);
    hr = consCmdList->Close();
    if (FAILED(hr)) {
        PrintJson("FAIL", "Close consumer command list failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    ID3D12CommandList* consLists[] = { consCmdList.Get() };
    consQueue->ExecuteCommandLists(1, consLists);

    // 14. Consumer local fence for completion
    ComPtr<ID3D12Fence> consLocalFence;
    hr = consDevice->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&consLocalFence));
    if (FAILED(hr)) {
        PrintJson("FAIL", "CreateFence consumer local failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    hr = consQueue->Signal(consLocalFence.Get(), kFenceValue);
    if (FAILED(hr)) {
        PrintJson("FAIL", "Signal consumer local fence failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    UniqueHandle hCompletionEvent(CreateEvent(nullptr, FALSE, FALSE, nullptr));
    if (!hCompletionEvent) {
        PrintJson("FAIL", "CreateEvent completion failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, E_FAIL);
        return 1;
    }

    hr = consLocalFence->SetEventOnCompletion(kFenceValue, hCompletionEvent.get());
    if (FAILED(hr)) {
        PrintJson("FAIL", "SetEventOnCompletion failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    DWORD waitResult = WaitForSingleObject(hCompletionEvent.get(), 10000);
    if (waitResult != WAIT_OBJECT_0) {
        PrintJson("FAIL", waitResult == WAIT_TIMEOUT ? "Consumer completion wait timed out after 10000ms"
                                                     : "WaitForSingleObject failed",
                  &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1,
                  waitResult == WAIT_TIMEOUT ? E_FAIL : HRESULT_FROM_WIN32(GetLastError()));
        return 1;
    }

    // 15. Verify readback
    BYTE* pReadData = nullptr;
    hr = consReadbackBuffer->Map(0, nullptr, reinterpret_cast<void**>(&pReadData));
    if (FAILED(hr)) {
        PrintJson("FAIL", "Map readback buffer failed", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory, 0, kTransport, -1, hr);
        return 1;
    }

    int64_t mismatchOffset = -1;
    for (UINT64 i = 0; i < kBufferSize; ++i) {
        BYTE expected = static_cast<BYTE>((i * 7 + 13) % 256);
        if (pReadData[i] != expected && mismatchOffset < 0) {
            mismatchOffset = static_cast<int64_t>(i);
        }
    }
    consReadbackBuffer->Unmap(0, nullptr);

    if (mismatchOffset >= 0) {
        PrintJson("FAIL", "Data mismatch after cross-adapter copy", &prodInfo->luid, &consInfo->luid,
                  prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
                  consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory,
                  kBufferSize, kTransport, mismatchOffset, S_OK);
        return 1;
    }

    PrintJson("PASS", "Cross-adapter shared buffer copy verified", &prodInfo->luid, &consInfo->luid,
              prodInfo->desc.DedicatedVideoMemory, prodInfo->desc.SharedSystemMemory,
              consInfo->desc.DedicatedVideoMemory, consInfo->desc.SharedSystemMemory,
              kBufferSize, kTransport, -1, S_OK);
    return 0;
}

