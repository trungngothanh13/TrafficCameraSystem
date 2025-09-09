using System;
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
    
    private Camera camera;
    private RenderTexture renderTexture;
    private Texture2D texture2D;
    private TcpListener server;
    private TcpClient client;
    private NetworkStream stream;
    private bool isStreaming = false;
    private Thread serverThread;
    
    void Start()
    {
        camera = GetComponent<Camera>();
        if (camera == null)
        {
            Debug.LogError("No Camera component found!");
            return;
        }
        
        // Create render texture for streaming
        renderTexture = new RenderTexture(720, 480, 24);
        texture2D = new Texture2D(720, 480, TextureFormat.RGB24, false);
        
        // Don't set targetTexture here - we'll use OnPostRender instead
        
        // Start TCP server
        StartServer();
        
        // Start streaming
        StartCoroutine(StreamFrames());
    }
    
    void StartServer()
    {
        try
        {
            server = new TcpListener(IPAddress.Any, port);
            server.Start();
            
            serverThread = new Thread(AcceptClients);
            serverThread.IsBackground = true;
            serverThread.Start();
            
            Debug.Log($"TCP Server started on port {port}");
        }
        catch (Exception e)
        {
            Debug.LogError($"Failed to start server: {e.Message}");
        }
    }
    
    void AcceptClients()
    {
        try
        {
            while (server != null && server.Server.IsBound)
            {
                try
                {
                    client = server.AcceptTcpClient();
                    stream = client.GetStream();
                    isStreaming = true;
                    
                    Debug.Log("Client connected!");
                    
                    // Wait for client to disconnect
                    while (client != null && client.Connected && isStreaming)
                    {
                        Thread.Sleep(100);
                    }
                    
                    Debug.Log("Client disconnected");
                    isStreaming = false;
                }
                catch (System.Net.Sockets.SocketException)
                {
                    // Server was stopped
                    break;
                }
            }
        }
        catch (System.Threading.ThreadAbortException)
        {
            // Thread was aborted, this is normal
            Debug.Log("Server thread stopped");
        }
        catch (Exception e)
        {
            Debug.LogError($"Server error: {e.Message}");
        }
    }
    
    System.Collections.IEnumerator StreamFrames()
    {
        float frameInterval = 1f / frameRate;
        
        while (true)
        {
            if (isStreaming && stream != null && stream.CanWrite)
            {
                SendFrame();
            }
            
            yield return new WaitForSeconds(frameInterval);
        }
    }
    
    void OnPostRender()
    {
        // This method is no longer needed - we use coroutine instead
    }
    
    void SendFrame()
    {
        try
        {
            // Check if client is still connected
            if (client == null || !client.Connected || stream == null || !stream.CanWrite)
            {
                isStreaming = false;
                return;
            }
            
            // Capture current camera view to texture
            camera.targetTexture = renderTexture;
            camera.Render();
            
            // Read pixels from render texture
            RenderTexture.active = renderTexture;
            texture2D.ReadPixels(new Rect(0, 0, 720, 480), 0, 0);
            texture2D.Apply();
            RenderTexture.active = null;
            
            // Reset camera to render to screen
            camera.targetTexture = null;
            
            // Convert to JPEG
            byte[] imageData = texture2D.EncodeToJPG(jpegQuality);
            
            // Send frame length (4 bytes, big-endian)
            byte[] lengthBytes = BitConverter.GetBytes(imageData.Length);
            if (BitConverter.IsLittleEndian)
            {
                Array.Reverse(lengthBytes);
            }
            
            // Send data
            stream.Write(lengthBytes, 0, 4);
            stream.Write(imageData, 0, imageData.Length);
            stream.Flush();
            
            Debug.Log($"Sent frame: {imageData.Length} bytes");
        }
        catch (System.Net.Sockets.SocketException)
        {
            // Client disconnected normally
            Debug.Log("Client disconnected");
            isStreaming = false;
        }
        catch (System.IO.IOException)
        {
            // Connection lost
            Debug.Log("Connection lost");
            isStreaming = false;
        }
        catch (Exception e)
        {
            Debug.LogError($"Frame send error: {e.Message}");
            isStreaming = false;
        }
    }
    
    void OnDestroy()
    {
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
            camera.targetTexture = null;
            renderTexture.Release();
            DestroyImmediate(renderTexture);
        }
        
        if (texture2D != null)
        {
            DestroyImmediate(texture2D);
        }
    }
}
