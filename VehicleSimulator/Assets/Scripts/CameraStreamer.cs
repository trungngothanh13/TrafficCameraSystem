using UnityEngine;
using UnityEngine.Rendering;
using Unity.Collections;
using System;

public class CameraStreamer : MonoBehaviour
{
    [Header("Camera Settings")]
    public Camera targetCamera;
    public int cameraId = 0;
    // Giảm mặc định để nhẹ hơn khi chạy nhiều camera
    public int width = 1280;
    public int height = 720;
    [Range(1, 100)] public int quality = 80;
    [Range(1f, 60f)] public float frameRate = 15f;
    
    [Header("WebSocket Settings")]
    public string serverUrl = "ws://127.0.0.1:8081";
    public bool autoConnect = true;
    public bool useExistingTargetTexture = true;
    
    [Header("Performance")]
    public bool useGPUReadback = true; // Dùng AsyncGPUReadback thay vì ReadPixels (nhanh hơn, không block)
    
    private RenderTexture renderTexture;
    private Texture2D texture2D;
    private WebSocketClient wsClient;
    private float lastFrameTime;
    private float frameInterval;
    private bool createdOwnRenderTexture = false;
    private RenderTexture originalTargetTexture;
    private bool isShuttingDown = false;
    
    // GPU Readback state
    private bool isGPUPending = false; // Đang chờ GPU readback
    
    void Start()
    {
        // Giữ lại targetTexture gốc (nếu có)
        originalTargetTexture = targetCamera != null ? targetCamera.targetTexture : null;

        // Sử dụng RenderTexture sẵn có nếu có và cờ được bật
        if (useExistingTargetTexture && targetCamera != null && targetCamera.targetTexture != null)
        {
            renderTexture = targetCamera.targetTexture;
            width = renderTexture.width;
            height = renderTexture.height;
            createdOwnRenderTexture = false;
        }
        else
        {
            // Khởi tạo render texture riêng
            renderTexture = new RenderTexture(width, height, 24);
            if (targetCamera != null)
            {
                targetCamera.targetTexture = renderTexture;
            }
            createdOwnRenderTexture = true;
        }
        
        // Khởi tạo texture2D để đọc pixel data
        texture2D = new Texture2D(width, height, TextureFormat.RGB24, false);
        
        // Tính toán frame interval
        frameInterval = Mathf.Max(0.001f, 1f / Mathf.Max(1f, frameRate));
        
        // Khởi tạo WebSocket client
        if (autoConnect)
        {
            ConnectToServer();
        }
    }
    
    void Update()
    {
        // Nếu đang tắt/đang disconnect thì không capture nữa
        if (isShuttingDown)
            return;

        // Kiểm tra nếu đã đến thời gian capture frame tiếp theo
        if (Time.time - lastFrameTime >= frameInterval)
        {
            CaptureAndSendFrame();
            lastFrameTime = Time.time;
        }
    }
    
    void CaptureAndSendFrame()
    {
        if (wsClient == null || !wsClient.IsConnected())
            return;
            
        if (renderTexture == null)
            return;
        
        // Nếu đang chờ GPU readback từ frame trước, bỏ qua frame này
        if (isGPUPending)
            return;

        if (useGPUReadback && SystemInfo.supportsAsyncGPUReadback)
        {
            // Dùng AsyncGPUReadback - không block main thread, nhanh hơn
            isGPUPending = true;
            AsyncGPUReadback.Request(renderTexture, 0, TextureFormat.RGB24, OnGPUReadbackComplete);
        }
        else
        {
            // Fallback: dùng ReadPixels (CPU, chậm hơn nhưng luôn hoạt động)
            RenderTexture prev = RenderTexture.active;
            RenderTexture.active = renderTexture;
            texture2D.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            texture2D.Apply(false);
            RenderTexture.active = prev;
            
            // Encode trực tiếp từ texture2D (đã có dữ liệu từ ReadPixels)
            byte[] jpegData = texture2D.EncodeToJPG(Mathf.Clamp(quality, 1, 100));
            byte[] packet = BuildBinaryPacket(cameraId, jpegData);
            wsClient.SendBytes(packet);
        }
    }
    
    void OnGPUReadbackComplete(AsyncGPUReadbackRequest request)
    {
        isGPUPending = false;
        
        if (isShuttingDown || wsClient == null || !wsClient.IsConnected())
            return;
        
        if (request.hasError)
        {
            Debug.LogWarning($"Camera {cameraId} GPU readback error, falling back to CPU");
            // Fallback to CPU if GPU readback fails
            return;
        }
        
        // Lấy dữ liệu từ GPU
        NativeArray<byte> data = request.GetData<byte>();
        ProcessAndSendFrame(data);
    }
    
    void ProcessAndSendFrame(NativeArray<byte> rawData)
    {
        if (isShuttingDown || wsClient == null || !wsClient.IsConnected())
            return;
        
        // Copy dữ liệu vào Texture2D để encode
        if (texture2D == null || texture2D.width != width || texture2D.height != height)
        {
            if (texture2D != null)
                Destroy(texture2D);
            texture2D = new Texture2D(width, height, TextureFormat.RGB24, false);
        }
        
        texture2D.LoadRawTextureData(rawData);
        texture2D.Apply(false);
        
        // Encode thành JPEG
        byte[] jpegData = texture2D.EncodeToJPG(Mathf.Clamp(quality, 1, 100));

        // Tạo packet binary và gửi qua WebSocket
        byte[] packet = BuildBinaryPacket(cameraId, jpegData);
        wsClient.SendBytes(packet);
    }

    // Packet binary: [1 byte camId][8 bytes ticks][4 bytes length][N bytes jpeg]
    byte[] BuildBinaryPacket(int camId, byte[] jpeg)
    {
        long ts = DateTime.UtcNow.Ticks;
        int len = jpeg.Length;

        byte[] packet = new byte[1 + 8 + 4 + len];
        packet[0] = (byte)camId;

        Buffer.BlockCopy(BitConverter.GetBytes(ts), 0, packet, 1, 8);
        Buffer.BlockCopy(BitConverter.GetBytes(len), 0, packet, 1 + 8, 4);
        Buffer.BlockCopy(jpeg, 0, packet, 1 + 8 + 4, len);

        return packet;
    }
    
    public void ConnectToServer()
    {
        if (wsClient != null)
        {
            wsClient.Disconnect();
        }

        isShuttingDown = false;
        wsClient = new WebSocketClient(serverUrl);
        wsClient.OnConnected += OnWebSocketConnected;
        wsClient.OnDisconnected += OnWebSocketDisconnected;
        wsClient.OnError += OnWebSocketError;
        wsClient.Connect();
    }
    
    public void DisconnectFromServer()
    {
        isShuttingDown = true;

        if (wsClient != null)
        {
            wsClient.Disconnect();
        }
    }
    
    void OnWebSocketConnected()
    {
        Debug.Log($"Camera {cameraId} connected to Python WebSocket server");
    }
    
    void OnWebSocketDisconnected()
    {
        Debug.Log($"Camera {cameraId} disconnected from Python WebSocket server");
    }
    
    void OnWebSocketError(string error)
    {
        // Bỏ qua các lỗi do cancel/đóng kết nối bình thường
        if (!string.IsNullOrEmpty(error) &&
            error.IndexOf("canceled", StringComparison.OrdinalIgnoreCase) >= 0)
        {
            return;
        }

        Debug.LogError($"Camera {cameraId} WebSocket error: {error}");
    }
    
    void OnDestroy()
    {
        isShuttingDown = true;
        DisconnectFromServer();

        // Chỉ thu hồi RenderTexture nếu do script tạo ra
        if (createdOwnRenderTexture && renderTexture != null)
        {
            if (targetCamera != null && targetCamera.targetTexture == renderTexture)
            {
                // Khôi phục targetTexture gốc trước khi hủy
                targetCamera.targetTexture = originalTargetTexture;
            }
            renderTexture.Release();
            DestroyImmediate(renderTexture);
        }

        if (texture2D != null)
        {
            Destroy(texture2D);
        }
    }
    
    void OnApplicationQuit()
    {
        isShuttingDown = true;
        DisconnectFromServer();
    }

    internal bool IsConnected()
    {
        return wsClient != null && wsClient.IsConnected();
    }
}
