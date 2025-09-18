using UnityEngine;
using System;

public class CameraStreamer : MonoBehaviour
{
    [Header("Camera Settings")]
    public Camera targetCamera;
    public int cameraId = 0;
    public int width = 1920;
    public int height = 1080;
    [Range(1, 100)] public int quality = 80;
    [Range(1f, 60f)] public float frameRate = 30f;
    
    [Header("WebSocket Settings")]
    public string serverUrl = "ws://127.0.0.1:8081";
    public bool autoConnect = true;
    public bool useExistingTargetTexture = true;
    
    private RenderTexture renderTexture;
    private Texture2D texture2D;
    private WebSocketClient wsClient;
    private float lastFrameTime;
    private float frameInterval;
    private bool createdOwnRenderTexture = false;
    private RenderTexture originalTargetTexture;
    
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
            
        // Đọc pixel data từ render texture
        if (renderTexture == null)
            return;

        RenderTexture prev = RenderTexture.active;
        RenderTexture.active = renderTexture;
        texture2D.ReadPixels(new Rect(0, 0, width, height), 0, 0);
        texture2D.Apply(false);
        RenderTexture.active = prev;
        
        // Encode thành JPEG
        byte[] jpegData = texture2D.EncodeToJPG(Mathf.Clamp(quality, 1, 100));
        
        // Tạo message với camera ID và frame data
        string message = CreateStreamMessage(cameraId, jpegData);
        
        // Gửi qua WebSocket
        wsClient.SendMessage(message);
    }
    
    string CreateStreamMessage(int camId, byte[] frameData)
    {
        // Format: "CAMERA_STREAM:{cameraId}:{base64Data}"
        string base64Data = Convert.ToBase64String(frameData);
        return $"CAMERA_STREAM:{camId}:{base64Data}";
    }
    
    public void ConnectToServer()
    {
        if (wsClient != null)
        {
            wsClient.Disconnect();
        }
        
        wsClient = new WebSocketClient(serverUrl);
        wsClient.OnConnected += OnWebSocketConnected;
        wsClient.OnDisconnected += OnWebSocketDisconnected;
        wsClient.OnError += OnWebSocketError;
        wsClient.Connect();
    }
    
    public void DisconnectFromServer()
    {
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
        Debug.LogError($"Camera {cameraId} WebSocket error: {error}");
    }
    
    void OnDestroy()
    {
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
            DestroyImmediate(texture2D);
        }
    }
    
    void OnApplicationQuit()
    {
        DisconnectFromServer();
    }

    internal bool IsConnected()
    {
        return wsClient != null && wsClient.IsConnected();
    }
}
