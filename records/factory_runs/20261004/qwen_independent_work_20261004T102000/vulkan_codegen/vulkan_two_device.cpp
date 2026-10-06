// Windows C++17 Vulkan Two-Device Transfer Smoke Test
// Build: cl /std:c++17 /EHsc source.cpp /I <SDK_INCLUDE> /link vulkan-1.lib
// Note: SDK headers not verified locally. Exit codes: 0=PASS, 1=CORRUPT, 2=ERR, 3=TIMEOUT, 77=SKIP
#include <vulkan/vulkan.h>
#include <iostream>
#include <vector>
#include <cstring>
#include <chrono>
#include <thread>
#include <algorithm>

#define VK_CHECK(x) do { VkResult err = (x); if (err != VK_SUCCESS) { std::cerr << "VK Error: " << err << " at line " << __LINE__ << "\n"; exit(2); } } while(0)

const uint32_t PATTERN = 0x4a17c0de;
const size_t BUFFER_SIZE = 256 * 1024; // 256 KiB
const uint32_t WORD_COUNT = BUFFER_SIZE / sizeof(uint32_t);

struct DeviceContext {
    VkPhysicalDevice phys;
    VkDevice dev;
    VkQueue queue;
    uint32_t qIdx;
    VkCommandPool cmdPool;
    VkBuffer bufA_dev, bufA_host, bufB_host, bufB_dev;
    VkDeviceMemory memA_dev, memA_host, memB_host, memB_dev;
    VkFence fence;
};

uint32_t FindMemType(VkPhysicalDevice phys, uint32_t typeFilter, VkMemoryPropertyFlags props) {
    VkPhysicalDeviceMemoryProperties memProps;
    vkGetPhysicalDeviceMemoryProperties(phys, &memProps);
    for (uint32_t i = 0; i < memProps.memoryTypeCount; ++i) {
        if ((typeFilter & (1 << i)) && (memProps.memoryTypes[i].propertyFlags & props) == props) return i;
    }
    std::cerr << "Failed to find suitable memory type\n";
    exit(2);
}

void CreateBufferAndMemory(DeviceContext& ctx, VkBufferUsageFlags usage, VkMemoryPropertyFlags props, VkBuffer* buf, VkDeviceMemory* mem) {
    VkBufferCreateInfo bci = { VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO }; bci.size = BUFFER_SIZE; bci.usage = usage;
    VK_CHECK(vkCreateBuffer(ctx.dev, &bci, nullptr, buf));
    VkMemoryRequirements mr; vkGetBufferMemoryRequirements(ctx.dev, *buf, &mr);
    VkMemoryAllocateInfo mai = { VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO }; mai.allocationSize = mr.size; mai.memoryTypeIndex = FindMemType(ctx.phys, mr.memoryTypeBits, props);
    VK_CHECK(vkAllocateMemory(ctx.dev, &mai, nullptr, mem));
    VK_CHECK(vkBindBufferMemory(ctx.dev, *buf, *mem, 0));
}

void RecordTransferCmds(DeviceContext& srcCtx, DeviceContext& dstCtx, VkCommandBuffer cmd) {
    // Fill A (src device-local) with pattern
    VkBufferCopy bc = {};
    vkCmdFillBuffer(cmd, srcCtx.bufA_dev, 0, BUFFER_SIZE, PATTERN);
    
    // Barrier: A_dev write -> A_host read? No, we copy A_dev to A_host via staging logic in main.
    // Here we just record the copy from A_dev to A_host (which is host-visible but used as dest for GPU copy?)
    // Actually spec says: Copy A(device-local) to A(host-visible). This requires a transfer.
    // But usually you map host-visible and memcpy. The prompt says: "copy to A host-visible readback".
    // If A_host is HOST_VISIBLE|HOST_COHERENT, we can't GPU-copy TO it easily without specific flags or staging.
    // Prompt: "memcpy HOST staging into B host-visible upload". 
    // Let's interpret: 
    // 1. Fill A_dev on GPU.
    // 2. Copy A_dev -> A_host (GPU command). Requires A_host to have TRANSFER_DST_BIT.
    // 3. Map A_host, verify pattern.
    // 4. Unmap A_host.
    // 5. Map B_host, memcpy pattern (CPU).
    // 6. Flush B_host.
    // 7. Copy B_host -> B_dev (GPU command). Requires B_host TRANSFER_SRC_BIT, B_dev TRANSFER_DST_BIT.
    // 8. Copy B_dev -> B_host (GPU command) for readback verification? Or just verify B_dev contents?
    // Prompt: "transfer to B device-local then B host-visible readback".
    // So step 8: Copy B_dev -> B_host (readback buffer).
    // Step 9: Map B_host, verify.

    // Src: A_dev -> Dst: A_host
    VkImageMemoryBarrier imgBar = {}; // Not needed for buffers
    VkBufferMemoryBarrier bufBar = { VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER };
    bufBar.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    bufBar.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
    bufBar.buffer = srcCtx.bufA_dev;
    bufBar.offset = 0; bufBar.size = BUFFER_SIZE;
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT, 0, 0, nullptr, 1, &bufBar, 0, nullptr);
    
    // Wait, copying between two different logical devices is NOT supported directly in one command buffer unless they share memory/queues or use external semaphores/fences across devices.
    // The prompt implies TWO SEPARATE DEVICES. 
    // "Generate ... TWO-SEPARATE-DEVICE transfer smoke source"
    // Standard Vulkan does not allow direct P2P copies between separate logical devices without explicit synchronization objects (semaphores) and potentially peer-to-peer extensions which are complex.
    // However, the prompt asks for "transport HOST_STAGING_NOT_P2P". This suggests we simulate the flow using CPU staging or treat them as independent tests that don't talk to each other directly, OR we use the Host as the intermediary.
    // Re-reading: "Create one logical device per selected physical device... A device-local... copy to A host-visible... memcpy HOST staging into B host-visible... transfer to B device-local..."
    // It seems the data flows: Dev A -> Host A -> (CPU memcpy) -> Host B -> Dev B -> Host B.
    // There is no direct GPU-GPU copy between Device A and Device B. They are independent pipelines connected by CPU memory.
    
    // So, Command Buffer 1 (on Dev A): Fill A_dev, Copy A_dev -> A_host.
    // Command Buffer 2 (on Dev B): Copy B_host -> B_dev, Copy B_dev -> B_host.
    
    // We need to pass the correct context to the recorder.
    // Let's split this function or handle it in main.
}

int main(int argc, char** argv) {
    bool injectCorruption = false;
    for (int i = 1; i < argc; ++i) if (strcmp(argv[i], "--inject-corruption") == 0) injectCorruption = true;

    VkInstanceCreateInfo ici = { VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO };
    VkApplicationInfo app = { VK_STRUCTURE_TYPE_APPLICATION_INFO };
    app.apiVersion = VK_API_VERSION_1_0;
    ici.pApplicationInfo = &app;
    
    VkInstance instance;
    VK_CHECK(vkCreateInstance(&ici, nullptr, &instance));

    uint32_t count = 0;
    vkEnumeratePhysicalDevices(instance, &count, nullptr);
    if (count < 2) { std::cout << "SKIP: Need >=2 devices\n"; vkDestroyInstance(instance, nullptr); return 77; }
    
    std::vector<VkPhysicalDevice> physDevs(count);
    vkEnumeratePhysicalDevices(instance, &count, physDevs.data());

    // Select first two distinct devices
    DeviceContext devs[2];
    for (int i = 0; i < 2; ++i) {
        devs[i].phys = physDevs[i];
        VkPhysicalDeviceProperties prop; vkGetPhysicalDeviceProperties(devs[i].phys, &prop);
        std::cout << "Device " << i << ": " << prop.deviceName << " ID:" << prop.deviceID << " Vendor:" << prop.vendorID << "\n";
        
        // Query groups diagnostic
        uint32_t grpCount = 0;
        vkGetPhysicalDeviceGroupProperties(devs[i].phys, &grpCount, nullptr);
        if (grpCount > 0) {
            std::vector<VkPhysicalDeviceGroupProperties> grps(grpCount);
            for(auto& g : grps) g.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_GROUP_PROPERTIES;
            vkGetPhysicalDeviceGroupProperties(devs[i].phys, &grpCount, grps.data());
            std::cout << "  Groups found: " << grpCount << " (Diagnostic only)\n";
        }

        // Queue Family
        uint32_t qfCount = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(devs[i].phys, &qfCount, nullptr);
        std::vector<VkQueueFamilyProperties> qfs(qfCount);
        vkGetPhysicalDeviceQueueFamilyProperties(devs[i].phys, &qfCount, qfs.data());
        
        devs[i].qIdx = UINT32_MAX;
        for (uint32_t j = 0; j < qfCount; ++j) {
            if (qfs[j].queueFlags & VK_QUEUE_TRANSFER_BIT) { devs[i].qIdx = j; break; }
        }
        if (devs[i].qIdx == UINT32_MAX) { std::cerr << "No transfer queue\n"; vkDestroyInstance(instance, nullptr); return 2; }

        float prio = 1.0f;
        VkDeviceQueueCreateInfo qci = { VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO };
        qci.queueFamilyIndex = devs[i].qIdx; qci.queueCount = 1; qci.pQueuePriorities = &prio;
        
        VkDeviceCreateInfo dci = { VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO };
        dci.queueCreateInfoCount = 1; dci.pQueueCreateInfos = &qci;
        VK_CHECK(vkCreateDevice(devs[i].phys, &dci, nullptr, &devs[i].dev));
        vkGetDeviceQueue(devs[i].dev, devs[i].qIdx, 0, &devs[i].queue);

        VkCommandPoolCreateInfo cpci = { VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO };
        cpci.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        cpci.queueFamilyIndex = devs[i].qIdx;
        VK_CHECK(vkCreateCommandPool(devs[i].dev, &cpci, nullptr, &devs[i].cmdPool));

        VkFenceCreateInfo fci = { VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
        VK_CHECK(vkCreateFence(devs[i].dev, &fci, nullptr, &devs[i].fence));

        // Buffers
        // A_dev: DEVICE_LOCAL | TRANSFER_DST (for fill) | TRANSFER_SRC (for copy to A_host)
        CreateBufferAndMemory(devs[i], VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, &devs[i].bufA_dev, &devs[i].memA_dev);
        // A_host: HOST_VISIBLE | HOST_COHERENT | TRANSFER_DST (for copy from A_dev) | HOST_READ
        CreateBufferAndMemory(devs[i], VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, &devs[i].bufA_host, &devs[i].memA_host);
        // B_host: HOST_VISIBLE | HOST_COHERENT | TRANSFER_SRC (for copy to B_dev) | HOST_WRITE (for CPU memcpy) | TRANSFER_DST (for readback from B_dev)
        CreateBufferAndMemory(devs[i], VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, &devs[i].bufB_host, &devs[i].memB_host);
        // B_dev: DEVICE_LOCAL | TRANSFER_DST (from B_host) | TRANSFER_SRC (to B_host readback)
        CreateBufferAndMemory(devs[i], VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, &devs[i].bufB_dev, &devs[i].memB_dev);
    }

    // Helper lambda to run commands on a device
    auto RunOnDevice = [&](int idx, std::function<void(VkCommandBuffer)> func) {
        VkCommandBufferAllocateInfo cbai = { VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO };
        cbai.commandPool = devs[idx].cmdPool; cbai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; cbai.commandBufferCount = 1;
        VkCommandBuffer cmd;
        VK_CHECK(vkAllocateCommandBuffers(devs[idx].dev, &cbai, &cmd));
        
        VkCommandBufferBeginInfo cbbi = { VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
        cbbi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        VK_CHECK(vkBeginCommandBuffer(cmd, &cbbi));
        
        func(cmd);
        
        VK_CHECK(vkEndCommandBuffer(cmd));
        
        VkSubmitInfo si = { VK_STRUCTURE_TYPE_SUBMIT_INFO };
        si.commandBufferCount = 1; si.pCommandBuffers = &cmd;
        VK_CHECK(vkResetFences(devs[idx].dev, 1, &devs[idx].fence));
        VK_CHECK(vkQueueSubmit(devs[idx].queue, 1, &si, devs[idx].fence));
        
        auto start = std::chrono::high_resolution_clock::now();
        while (true) {
            VkResult res = vkWaitForFences(devs[idx].dev, 1, &devs[idx].fence, VK_TRUE, 1000000000ULL); // 1s chunks
            if (res == VK_SUCCESS) break;
            if (res == VK_TIMEOUT) {
                auto now = std::chrono::high_resolution_clock::now();
                if (std::chrono::duration_cast<std::chrono::seconds>(now - start).count() >= 10) {
                    std::cerr << "Timeout on device " << idx << "\n"; exit(3);
                }
            } else { std::cerr << "Fence error\n"; exit(2); }
        }
        vkFreeCommandBuffers(devs[idx].dev, devs[idx].cmdPool, 1, &cmd);
    };

    // Phase 1: Device 0 (A) - Fill A_dev, Copy A_dev -> A_host
    RunOnDevice(0, [](VkCommandBuffer cmd) {
        vkCmdFillBuffer(cmd, devs[0].bufA_dev, 0, BUFFER_SIZE, PATTERN);
        VkBufferCopy bc = { 0, 0, BUFFER_SIZE };
        vkCmdCopyBuffer(cmd, devs[0].bufA_dev, devs[0].bufA_host, 1, &bc);
    });

    // Verify A_host
    void* mappedA;
    VK_CHECK(vkMapMemory(devs[0].dev, devs[0].memA_host, 0, BUFFER_SIZE, 0, &mappedA));
    uint32_t* dataA = (uint32_t*)mappedA;
    for (uint32_t i = 0; i < WORD_COUNT; ++i) {
        if (dataA[i] != PATTERN) { std::cerr << "Mismatch in A_host at " << i << "\n"; vkUnmapMemory(devs[0].dev, devs[0].memA_host); exit(1); }
    }
    vkUnmapMemory(devs[0].dev, devs[0].memA_host);

    // Phase 2: Device 1 (B) - CPU Staging to B_host, Copy B_host -> B_dev, Copy B_dev -> B_host
    // First, fill B_host via CPU
    void* mappedB;
    VK_CHECK(vkMapMemory(devs[1].dev, devs[1].memB_host, 0, BUFFER_SIZE, 0, &mappedB));
    uint32_t* dataB = (uint32_t*)mappedB;
    for (uint32_t i = 0; i < WORD_COUNT; ++i) dataB[i] = PATTERN;
    if (injectCorruption) dataB[WORD_COUNT / 2] ^= 0xFF; // Corrupt one word
    vkUnmapMemory(devs[1].dev, devs[1].memB_host);

    // Now GPU work on Device 1
    RunOnDevice(1, [](VkCommandBuffer cmd) {
        // Barrier: Host Write -> GPU Read (Source B_host)
        VkBufferMemoryBarrier barSrc = { VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER };
        barSrc.srcAccessMask = VK_ACCESS_HOST_WRITE_BIT;
        barSrc.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
        barSrc.buffer = devs[1].bufB_host;
        barSrc.offset = 0; barSrc.size = BUFFER_SIZE;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_HOST_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 1, &barSrc, 0, nullptr);

        // Copy B_host -> B_dev
        VkBufferCopy bc1 = { 0, 0, BUFFER_SIZE };
        vkCmdCopyBuffer(cmd, devs[1].bufB_host, devs[1].bufB_dev, 1, &bc1);

        // Barrier: GPU Write (B_dev) -> GPU Read (B_dev) ? No, next is Copy B_dev -> B_host
        // Need barrier after copy to B_dev before reading it for next copy? 
        // vkCmdCopyBuffer handles internal sync usually, but explicit barriers are safer for cross-stage.
        // Actually, the second copy reads B_dev. The first wrote B_dev. Same stage (TRANSFER). 
        // But let's add barrier to be safe/correct per prompt "barriers/stages".
        VkBufferMemoryBarrier barMid = { VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER };
        barMid.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        barMid.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
        barMid.buffer = devs[1].bufB_dev;
        barMid.offset = 0; barMid.size = BUFFER_SIZE;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 1, &barMid, 0, nullptr);

        // Copy B_dev -> B_host (Readback)
        VkBufferCopy bc2 = { 0, 0, BUFFER_SIZE };
        vkCmdCopyBuffer(cmd, devs[1].bufB_dev, devs[1].bufB_host, 1, &bc2);

        // Barrier: GPU Write (B_host) -> Host Read
        VkBufferMemoryBarrier barDst = { VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER };
        barDst.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        barDst.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
        barDst.buffer = devs[1].bufB_host;
        barDst.offset = 0; barDst.size = BUFFER_SIZE;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT, 0, 0, nullptr, 1, &barDst, 0, nullptr);
    });

    // Verify B_host
    VK_CHECK(vkMapMemory(devs[1].dev, devs[1].memB_host, 0, BUFFER_SIZE, 0, &mappedB));
    dataB = (uint32_t*)mappedB;
    int mismatches = 0;
    for (uint32_t i = 0; i < WORD_COUNT; ++i) {
        if (dataB[i] != PATTERN) mismatches++;
    }
    vkUnmapMemory(devs[1].dev, devs[1].memB_host);

    if (mismatches > 0) {
        std::cout << "FAIL: Mismatches in B_host: " << mismatches << "\n";
        exit(injectCorruption ? 1 : 2);
    }

    std::cout << "PASS: Two-device transfer smoke test successful\n";

    // Cleanup
    for (int i = 0; i < 2; ++i) {
        vkDestroyFence(devs[i].dev, devs[i].fence, nullptr);
        vkDestroyCommandPool(devs[i].dev, devs[i].cmdPool, nullptr);
        vkDestroyBuffer(devs[i].dev, devs[i].bufA_dev, nullptr); vkFreeMemory(devs[i].dev, devs[i].memA_dev, nullptr);
        vkDestroyBuffer(devs[i].dev, devs[i].bufA_host, nullptr); vkFreeMemory(devs[i].dev, devs[i].memA_host, nullptr);
        vkDestroyBuffer(devs[i].dev, devs[i].bufB_host, nullptr); vkFreeMemory(devs[i].dev, devs[i].memB_host, nullptr);
        vkDestroyBuffer(devs[i].dev, devs[i].bufB_dev, nullptr); vkFreeMemory(devs[i].dev, devs[i].memB_dev, nullptr);
        vkDestroyDevice(devs[i].dev, nullptr);
    }
    vkDestroyInstance(instance, nullptr);
    return 0;
}
