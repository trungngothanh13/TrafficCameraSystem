using UnityEngine;

public class CameraManager : MonoBehaviour
{
    [Header("Camera Configuration")]
    public Camera[] cameras = new Camera[4];
    public CameraStreamer[] cameraStreamers = new CameraStreamer[4];
    
    [Header("Server Settings")]
    public string serverUrl = "ws://127.0.0.1:8081";
    public bool startStreamingOnStart = true;
    
    [Header("Stream Settings")]
    public int width = 1920;
    public int height = 1080;
    public int quality = 80;
    public float frameRate = 30f;
    
    void Start()
    {
        SetupCameras();
        
        if (startStreamingOnStart)
        {
            StartAllStreams();
        }
    }
    
    void SetupCameras()
    {
        for (int i = 0; i < cameras.Length; i++)
        {
            if (cameras[i] != null)
            {
                // Tạo CameraStreamer component
                CameraStreamer streamer = cameras[i].gameObject.GetComponent<CameraStreamer>();
                if (streamer == null)
                {
                    streamer = cameras[i].gameObject.AddComponent<CameraStreamer>();
                }
                
                // Cấu hình streamer
                streamer.targetCamera = cameras[i];
                streamer.cameraId = i;
                streamer.serverUrl = serverUrl;
                streamer.width = width;
                streamer.height = height;
                streamer.quality = quality;
                streamer.frameRate = frameRate;
                streamer.autoConnect = false; // Sẽ connect thủ công
                
                cameraStreamers[i] = streamer;
                
                Debug.Log($"Setup camera {i}: {cameras[i].name}");
            }
        }
    }
    
    public void StartAllStreams()
    {
        for (int i = 0; i < cameraStreamers.Length; i++)
        {
            if (cameraStreamers[i] != null)
            {
                cameraStreamers[i].ConnectToServer();
            }
        }
        
        Debug.Log("Started all camera streams to Python server");
    }
    
    public void StopAllStreams()
    {
        for (int i = 0; i < cameraStreamers.Length; i++)
        {
            if (cameraStreamers[i] != null)
            {
                cameraStreamers[i].DisconnectFromServer();
            }
        }
        
        Debug.Log("Stopped all camera streams");
    }
    
    public void StartStream(int cameraIndex)
    {
        if (cameraIndex >= 0 && cameraIndex < cameraStreamers.Length && cameraStreamers[cameraIndex] != null)
        {
            cameraStreamers[cameraIndex].ConnectToServer();
            Debug.Log($"Started stream for camera {cameraIndex}");
        }
    }
    
    public void StopStream(int cameraIndex)
    {
        if (cameraIndex >= 0 && cameraIndex < cameraStreamers.Length && cameraStreamers[cameraIndex] != null)
        {
            cameraStreamers[cameraIndex].DisconnectFromServer();
            Debug.Log($"Stopped stream for camera {cameraIndex}");
        }
    }
    
    void OnGUI()
    {
        GUILayout.BeginArea(new Rect(10, 10, 300, 200));
        GUILayout.Label("Camera Stream Manager (Python Server)", GUI.skin.box);
        
        if (GUILayout.Button("Start All Streams"))
        {
            StartAllStreams();
        }
        
        if (GUILayout.Button("Stop All Streams"))
        {
            StopAllStreams();
        }
        
        GUILayout.Space(10);
        
        for (int i = 0; i < cameraStreamers.Length; i++)
        {
            if (cameraStreamers[i] != null)
            {
                string status = cameraStreamers[i].IsConnected() ? "Connected" : "Disconnected";
                GUILayout.Label($"Camera {i}: {status}");
            }
        }
        
        GUILayout.EndArea();
    }
    
    void OnDestroy()
    {
        StopAllStreams();
    }
    
    void OnApplicationQuit()
    {
        StopAllStreams();
    }
}
