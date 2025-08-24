using System;
using System.Collections;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

public class CameraStreamer : MonoBehaviour
{
    [Header("Stream Settings")]
    public int port = 5001;
    public int jpegQuality = 75;
    public float frameRate = 60f;
    
    // Private variables
    private Camera targetCamera;
    private RenderTexture renderTexture;
    private Texture2D texture2D;
    private TcpListener server;
    private TcpClient client;
    private NetworkStream stream;
    private bool isStreaming = false;
    private Thread serverThread;
    
    void Start()
    {
        Debug.Log("Starting Camera Streamer...");
        
        // Get camera component
        targetCamera = GetComponent<Camera>();
        if (targetCamera == null)
        {
            Debug.LogError("No Camera component found! Please attach this script to a Camera.");
            return;
        }
        
        // Setup render texture
        renderTexture = new RenderTexture(640, 480, 24);
        texture2D = new Texture2D(640, 480, TextureFormat.RGB24, false);
        targetCamera.targetTexture = renderTexture;
        
        // Start TCP server
        StartTCPServer();
        
        // Start streaming coroutine
        StartCoroutine(StreamFrames());
        
        Debug.Log($"Camera Streamer initialized on port {port}");
    }
    
    void StartTCPServer()
    {
        try
        {
            server = new TcpListener(IPAddress.Any, port);
            server.Start();
            
            serverThread = new Thread(AcceptClients);
            serverThread.IsBackground = true;
            serverThread.Start();
            
            Debug.Log($"TCP Server started on port {port}");
            Debug.Log("Waiting for Python client to connect...");
        }
        catch (Exception e)
        {
            Debug.LogError($"Failed to start TCP server: {e.Message}");
        }
    }
    
    void AcceptClients()
    {
        try
        {
            while (true)
            {
                client = server.AcceptTcpClient();
                stream = client.GetStream();
                isStreaming = true;
                
                Debug.Log("✅ Python client connected!");
                
                // Handle client disconnection
                while (client.Connected && isStreaming)
                {
                    Thread.Sleep(100);
                }
                
                Debug.Log("Client disconnected");
                isStreaming = false;
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"TCP server error: {e.Message}");
        }
    }
    
    IEnumerator StreamFrames()
    {
        float frameInterval = 1f / frameRate;
        
        while (true)
        {
            if (isStreaming && stream != null && stream.CanWrite)
            {
                CaptureAndSendFrame();
            }
            
            yield return new WaitForSeconds(frameInterval);
        }
    }
    
    void CaptureAndSendFrame()
    {
        try
        {
            // Capture frame from camera
            RenderTexture.active = renderTexture;
            texture2D.ReadPixels(new Rect(0, 0, 640, 480), 0, 0);
            texture2D.Apply();
            RenderTexture.active = null;
            
            // Convert to JPEG
            byte[] imageData = texture2D.EncodeToJPG(jpegQuality);
            
            // Send frame length (4 bytes, big-endian)
            byte[] lengthBytes = BitConverter.GetBytes(imageData.Length);
            if (BitConverter.IsLittleEndian)
            {
                Array.Reverse(lengthBytes); // Convert to big-endian
            }
            
            // Send data
            stream.Write(lengthBytes, 0, 4);
            stream.Write(imageData, 0, imageData.Length);
            stream.Flush();
        }
        catch (Exception e)
        {
            Debug.LogError($"Frame capture/send error: {e.Message}");
            isStreaming = false;
        }
    }
    
    void OnDestroy()
    {
        Debug.Log("Stopping Camera Streamer...");
        
        isStreaming = false;
        
        if (stream != null)
        {
            stream.Close();
        }
        
        if (client != null)
        {
            client.Close();
        }
        
        if (server != null)
        {
            server.Stop();
        }
        
        if (serverThread != null)
        {
            serverThread.Abort();
        }
        
        if (renderTexture != null)
        {
            renderTexture.Release();
            DestroyImmediate(renderTexture);
        }
        
        if (texture2D != null)
        {
            DestroyImmediate(texture2D);
        }
    }
    
    // Simple GUI for debugging
    void OnGUI()
    {
        GUILayout.BeginArea(new Rect(10, 10, 250, 100));
        GUILayout.Label($"Camera Streamer");
        GUILayout.Label($"Port: {port}");
        GUILayout.Label($"Status: {(isStreaming ? "Streaming" : "Waiting for client")}");
        GUILayout.Label($"Client: {(client != null && client.Connected ? "Connected" : "Disconnected")}");
        GUILayout.EndArea();
    }
}