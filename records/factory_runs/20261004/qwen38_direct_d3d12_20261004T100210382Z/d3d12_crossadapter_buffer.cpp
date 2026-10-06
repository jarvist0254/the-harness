#include <windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <wrl/client.h>
#include <vector>
#include <string>
#include <iostream>
#include <iomanip>
#include <algorithm>

using Microsoft::WRL::ComPtr;

// Helper to print JSON result
void PrintResult(const std::string& status, const std::string& reason, HRESULT hr = S_OK) {
    // Escape quotes in reason if necessary (simple approach)
    std::string safeReason = reason;
    for (char& c : safeReason) {
        if (c == '"') c = '\\"';
    }
    std::cout << "{\"status\": \"" << status << "\", \"reason\": \"" << safeReason << "\", \"hr\": " << hr << "}" << std::endl;
}

struct AdapterInfo {
    ComPtr<IDXGIAdapter1> adapter;
    LUID luid;
    DXGI_ADAPTER_DESC1 desc;
};

int main() {
    // 1. Enumerate Physical Adapters
    ComPtr<IDXGIFactory4> factory;
    HRESULT hr = CreateDXGIFactory1(IID_PPV_ARGS(&factory));
    if (FAILED(hr)) {
        PrintResult("FAIL", "Failed to create DXGI Factory", hr);
        return 1;
    }

    std::vector<AdapterInfo> physicalAdapters;
    for (UINT i = 0; ; ++i) {
        ComPtr<IDXGIAdapter1> adapter;
        hr = factory->EnumAdapters1(i, &adapter);
        if (hr == DXGI_ERROR_NOT_FOUND) break;
        if (FAILED(hr)) continue;

        DXGI_ADAPTER_DESC1 desc;
        adapter->GetDesc1(&desc);

        // Exclude software adapters and non-physical ones
        if ((desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) != 0) continue;
        
        // Check if it supports D3D12
        ComPtr<ID3D12Device> testDevice;
        hr = D3D12CreateDevice(adapter.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&testDevice));
        if (SUCCEEDED(hr)) {
            AdapterInfo info;
            info.adapter = adapter;
            info.luid = desc.AdapterLuid;
            info.desc = desc;
            physicalAdapters.push_back(info);
        }
    }

    if (physicalAdapters.size() < 2) {
        PrintResult("UNSUPPORTED", "Fewer than 2 physical compatible devices found");
        return 0;
    }

    // Choose two distinct adapters
    // Note: In a real scenario, we might want to check specific capabilities, 
    // but for this smoke test, we assume the first two valid ones.
    AdapterInfo& prodAdapter = physicalAdapters[0];
    AdapterInfo& consAdapter = physicalAdapters[1];

    // Ensure they are distinct
    if (prodAdapter.luid.HighPart == consAdapter.luid.HighPart && prodAdapter.luid.LowPart == consAdapter.luid.LowPart) {
        PrintResult("UNSUPPORTED", "Selected adapters are identical");
        return 0;
    }

    // 2. Create Devices and Queues
    ComPtr<ID3D12Device> prodDevice;
    ComPtr<ID3D12CommandQueue> prodQueue;
    ComPtr<ID3D12Device> consDevice;
    ComPtr<ID3D12CommandQueue> consQueue;

    hr = D3D12CreateDevice(prodAdapter.adapter.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&prodDevice));
    if (FAILED(hr)) {
        PrintResult("FAIL", "Failed to create Producer Device", hr);
        return 1;
    }

    hr = D3D12CreateDevice(consAdapter.adapter.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&consDevice));
    if (FAILED(hr)) {
        PrintResult("FAIL", "Failed to create Consumer Device", hr);
        return 1;
    }

    // Create Copy Queues
    D3D12_COMMAND_QUEUE_DESC queueDesc = {};
    queueDesc.Type = D3D12_COMMAND_LIST_TYPE_COPY;
    queueDesc.Flags = D3D12_COMMAND_QUEUE_FLAG_NONE;

    hr = prodDevice->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&prodQueue));
    if (FAILED(hr)) {
        PrintResult("FAIL", "Failed to create Producer Copy Queue", hr);
        return 1;
    }

    hr = consDevice->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&consQueue));
    if (FAILED(hr)) {
        PrintResult("FAIL", "Failed to create Consumer Copy Queue", hr);
        return 1;
    }

    // 3. Allocate Shared Cross-Adapter Buffer
    const UINT64 bufferSize = 256 * 1024; // 256 KiB
    
    // Producer creates the shared resource
    D3D12_HEAP_PROPERTIES heapProps = {};
    heapProps.Type = D3D12_HEAP_TYPE_CUSTOM;
    heapProps.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    heapProps.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;
    heapProps.CreationNodeMask = 1;
    heapProps.VisibleNodeMask = 1;
    // For cross-adapter sharing, we typically use DEFAULT or UPLOAD on the producer side 
    // but with SHARED_CROSS_ADAPTER flag. However, standard practice for explicit copy 
    // often involves creating a buffer on one device and opening it on another.
    // The key is the Heap Flags.
    
    // Let's try creating a buffer on the Producer device that can be shared.
    // We need to ensure the heap allows sharing.
    heapProps.Type = D3D12_HEAP_TYPE_DEFAULT; // Or CUSTOM depending on driver support
    
    D3D12_RESOURCE_DESC resourceDesc = {};
    resourceDesc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
    resourceDesc.Alignment = 0;
    resourceDesc.Width = bufferSize;
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
        IID_PPV_ARGS(&prodSharedBuffer)
    );

    if (FAILED(hr)) {
        PrintResult("UNSUPPORTED", "Failed to create shared cross-adapter buffer on Producer", hr);
        return 0;
    }

    // Get NT Handle from Producer
    HANDLE hSharedHandle = nullptr;
    hr = prodDevice->CreateSharedHandle(prodSharedBuffer.Get(), nullptr, GENERIC_ALL, nullptr, &hSharedHandle);
    if (FAILED(hr)) {
        PrintResult("FAIL", "Failed to create shared handle on Producer", hr);
        return 1;
    }

    // Open Shared Handle on Consumer
    ComPtr<ID3D12Resource> consSharedBuffer;
    hr = consDevice->OpenSharedHandle(hSharedHandle, IID_PPV_ARGS(&consSharedBuffer));
    if (FAILED(hr)) {
        CloseHandle(hSharedHandle);
        PrintResult("UNSUPPORTED", "Failed to open shared handle on Consumer", hr);
        return 0;
    }

    // 4. Setup Fences for Synchronization
    // Producer Fence
    ComPtr<ID3D12Fence> prodFence;
    hr = prodDevice->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&prodFence));
    if (FAILED(hr)) {
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create producer fence", hr);
        return 1;
    }

    HANDLE hProdFenceEvent = CreateEvent(nullptr, FALSE, FALSE, nullptr);
    if (!hProdFenceEvent) {
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create event", hr);
        return 1;
    }

    // Consumer Fence (Waitable)
    ComPtr<ID3D12Fence> consFence;
    hr = consDevice->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&consFence));
    if (FAILED(hr)) {
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create consumer fence", hr);
        return 1;
    }

    HANDLE hConsFenceEvent = CreateEvent(nullptr, FALSE, FALSE, nullptr);
    if (!hConsFenceEvent) {
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create event", hr);
        return 1;
    }

    // To synchronize across adapters, we usually rely on the OS-level synchronization 
    // via events or polling, as direct GPU-to-GPU fence signaling across different 
    // vendors/devices isn't always supported directly without specific APIs like 
    // ID3D12Device::OpenSharedHandle for fences (which requires D3D12_FENCE_FLAG_SHARED).
    
    // Let's recreate fences with SHARED flag to allow cross-device visibility if possible.
    // Actually, standard cross-adapter sync often uses CPU-side waiting on events 
    // triggered by GPU completion, or using a shared memory region for flags.
    // Given the complexity of true GPU-GPU fence sharing across arbitrary adapters,
    // we will simulate the flow:
    // 1. Producer writes data.
    // 2. Producer signals its own fence.
    // 3. CPU waits for Producer fence.
    // 4. CPU tells Consumer to wait/read (simulating publish).
    // 5. Consumer reads back.
    
    // For a strict "smoke test" of the API path, we verify the buffer creation/opening works.
    // Full cross-adapter fence sharing is highly driver-dependent. 
    // We will proceed with CPU-mediated synchronization for reliability in this generic test.

    // 5. Producer Upload and Copy
    // Create an upload buffer on Producer
    D3D12_HEAP_PROPERTIES uploadHeapProps = {};
    uploadHeapProps.Type = D3D12_HEAP_TYPE_UPLOAD;
    uploadHeapProps.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    uploadHeapProps.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;

    D3D12_RESOURCE_DESC uploadDesc = {};
    uploadDesc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
    uploadDesc.Width = bufferSize;
    uploadDesc.Height = 1;
    uploadDesc.DepthOrArraySize = 1;
    uploadDesc.MipLevels = 1;
    uploadDesc.Format = DXGI_FORMAT_UNKNOWN;
    uploadDesc.SampleDesc.Count = 1;
    uploadDesc.SampleDesc.Quality = 0;
    uploadDesc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    uploadDesc.Flags = D3D12_RESOURCE_FLAG_NONE;

    ComPtr<ID3D12Resource> prodUploadBuffer;
    hr = prodDevice->CreateCommittedResource(
        &uploadHeapProps,
        D3D12_HEAP_FLAG_NONE,
        &uploadDesc,
        D3D12_RESOURCE_STATE_GENERIC_READ,
        nullptr,
        IID_PPV_ARGS(&prodUploadBuffer)
    );
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create upload buffer", hr);
        return 1;
    }

    // Fill deterministic pattern
    BYTE* pData = nullptr;
    hr = prodUploadBuffer->Map(0, nullptr, reinterpret_cast<void**>(&pData));
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to map upload buffer", hr);
        return 1;
    }

    for (UINT64 i = 0; i < bufferSize; ++i) {
        pData[i] = static_cast<BYTE>(i % 256);
    }
    prodUploadBuffer->Unmap(0, nullptr);

    // Create Command List for Producer
    ComPtr<ID3D12CommandAllocator> prodCmdAlloc;
    ComPtr<ID3D12GraphicsCommandList> prodCmdList;
    hr = prodDevice->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY, IID_PPV_ARGS(&prodCmdAlloc));
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create command allocator", hr);
        return 1;
    }

    hr = prodDevice->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_COPY, prodCmdAlloc.Get(), nullptr, IID_PPV_ARGS(&prodCmdList));
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create command list", hr);
        return 1;
    }

    // Transition shared buffer to COPY_DEST
    D3D12_RESOURCE_BARRIER barrier = {};
    barrier.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    barrier.Transition.pResource = prodSharedBuffer.Get();
    barrier.Transition.StateBefore = D3D12_RESOURCE_STATE_COMMON;
    barrier.Transition.StateAfter = D3D12_RESOURCE_STATE_COPY_DEST;
    barrier.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;

    prodCmdList->Reset(prodCmdAlloc.Get(), nullptr);
    prodCmdList->ResourceBarrier(1, &barrier);
    prodCmdList->CopyResource(prodSharedBuffer.Get(), prodUploadBuffer.Get());
    
    // Signal fence
    UINT64 fenceValue = 1;
    prodCmdList->Close();
    
    ID3D12CommandList* ppCommandLists[] = { prodCmdList.Get() };
    prodQueue->ExecuteCommandLists(_countof(ppCommandLists), ppCommandLists);
    prodQueue->Signal(prodFence.Get(), fenceValue);

    // Wait for Producer Completion
    while (prodFence->GetCompletedValue() < fenceValue) {
        hr = prodFence->SetEventOnCompletion(fenceValue, hProdFenceEvent);
        if (FAILED(hr)) {
             CloseHandle(hConsFenceEvent);
             CloseHandle(hProdFenceEvent);
             CloseHandle(hSharedHandle);
             PrintResult("FAIL", "Failed to set event on completion", hr);
             return 1;
        }
        WaitForSingleObject(hProdFenceEvent, INFINITE);
    }

    // 6. Consumer Readback
    // Create readback buffer on Consumer
    D3D12_HEAP_PROPERTIES readbackHeapProps = {};
    readbackHeapProps.Type = D3D12_HEAP_TYPE_READBACK;
    readbackHeapProps.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    readbackHeapProps.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;

    D3D12_RESOURCE_DESC readbackDesc = {};
    readbackDesc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
    readbackDesc.Width = bufferSize;
    readbackDesc.Height = 1;
    readbackDesc.DepthOrArraySize = 1;
    readbackDesc.MipLevels = 1;
    readbackDesc.Format = DXGI_FORMAT_UNKNOWN;
    readbackDesc.SampleDesc.Count = 1;
    readbackDesc.SampleDesc.Quality = 0;
    readbackDesc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    readbackDesc.Flags = D3D12_RESOURCE_FLAG_NONE;

    ComPtr<ID3D12Resource> consReadbackBuffer;
    hr = consDevice->CreateCommittedResource(
        &readbackHeapProps,
        D3D12_HEAP_FLAG_NONE,
        &readbackDesc,
        D3D12_RESOURCE_STATE_COPY_DEST,
        nullptr,
        IID_PPV_ARGS(&consReadbackBuffer)
    );
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create readback buffer", hr);
        return 1;
    }

    // Create Command List for Consumer
    ComPtr<ID3D12CommandAllocator> consCmdAlloc;
    ComPtr<ID3D12GraphicsCommandList> consCmdList;
    hr = consDevice->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_COPY, IID_PPV_ARGS(&consCmdAlloc));
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create consumer command allocator", hr);
        return 1;
    }

    hr = consDevice->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_COPY, consCmdAlloc.Get(), nullptr, IID_PPV_ARGS(&consCmdList));
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to create consumer command list", hr);
        return 1;
    }

    // Transition shared buffer to COPY_SRC on Consumer side?
    // Note: The state of the shared resource is global. 
    // After Producer finished, it was in COPY_DEST. 
    // We need to transition it to COPY_SRC for the Consumer to read it.
    // This requires a barrier on the Consumer's command list.
    
    D3D12_RESOURCE_BARRIER barrierSrc = {};
    barrierSrc.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    barrierSrc.Transition.pResource = consSharedBuffer.Get();
    barrierSrc.Transition.StateBefore = D3D12_RESOURCE_STATE_COPY_DEST; // State left by producer
    barrierSrc.Transition.StateAfter = D3D12_RESOURCE_STATE_COPY_SRC;
    barrierSrc.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;

    consCmdList->Reset(consCmdAlloc.Get(), nullptr);
    consCmdList->ResourceBarrier(1, &barrierSrc);
    consCmdList->CopyResource(consReadbackBuffer.Get(), consSharedBuffer.Get());
    consCmdList->Close();

    ID3D12CommandList* ppConsCommandLists[] = { consCmdList.Get() };
    consQueue->ExecuteCommandLists(_countof(ppConsCommandLists), ppConsCommandLists);
    
    UINT64 consFenceValue = 1;
    consQueue->Signal(consFence.Get(), consFenceValue);

    // Wait for Consumer Completion
    while (consFence->GetCompletedValue() < consFenceValue) {
        hr = consFence->SetEventOnCompletion(consFenceValue, hConsFenceEvent);
        if (FAILED(hr)) {
             CloseHandle(hConsFenceEvent);
             CloseHandle(hProdFenceEvent);
             CloseHandle(hSharedHandle);
             PrintResult("FAIL", "Failed to set event on completion", hr);
             return 1;
        }
        WaitForSingleObject(hConsFenceEvent, INFINITE);
    }

    // Verify Data
    BYTE* pReadData = nullptr;
    hr = consReadbackBuffer->Map(0, nullptr, reinterpret_cast<void**>(&pReadData));
    if (FAILED(hr)) {
        CloseHandle(hConsFenceEvent);
        CloseHandle(hProdFenceEvent);
        CloseHandle(hSharedHandle);
        PrintResult("FAIL", "Failed to map readback buffer", hr);
        return 1;
    }

    bool match = true;
    for (UINT64 i = 0; i < bufferSize; ++i) {
        if (pReadData[i] != static_cast<BYTE>(i % 256)) {
            match = false;
            break;
        }
    }
    consReadbackBuffer->Unmap(0, nullptr);

    // Cleanup Handles
    CloseHandle(hConsFenceEvent);
    CloseHandle(hProdFenceEvent);
    CloseHandle(hSharedHandle);

    if (match) {
        PrintResult("PASS", "Cross-adapter buffer copy verified successfully");
    } else {
        PrintResult("FAIL", "Data mismatch after cross-adapter copy");
    }

    return 0;
}
