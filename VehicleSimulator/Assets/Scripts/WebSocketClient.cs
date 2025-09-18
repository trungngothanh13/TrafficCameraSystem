using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public class WebSocketClient
{
    private ClientWebSocket webSocket;
    private Uri serverUri;
    private CancellationTokenSource cancellationTokenSource;
    private bool isConnected = false;
    
    public event Action OnConnected;
    public event Action OnDisconnected;
    public event Action<string> OnError;
    public event Action<string> OnMessageReceived;
    
    public WebSocketClient(string url)
    {
        serverUri = new Uri(url);
        webSocket = new ClientWebSocket();
        // Tránh dùng proxy hệ thống gây lỗi header
        webSocket.Options.Proxy = null;
        // Giữ kết nối ổn định
        webSocket.Options.KeepAliveInterval = TimeSpan.FromSeconds(20);
        cancellationTokenSource = new CancellationTokenSource();
    }
    
    public async void Connect()
    {
        try
        {
            if (webSocket == null)
            {
                webSocket = new ClientWebSocket();
                webSocket.Options.Proxy = null;
                webSocket.Options.KeepAliveInterval = TimeSpan.FromSeconds(20);
            }
            if (cancellationTokenSource == null || cancellationTokenSource.IsCancellationRequested)
            {
                cancellationTokenSource = new CancellationTokenSource();
            }
            await webSocket.ConnectAsync(serverUri, cancellationTokenSource.Token);
            isConnected = true;
            OnConnected?.Invoke();
            
            // Bắt đầu listen cho messages
            _ = Task.Run(ReceiveMessages);
        }
        catch (WebSocketException wex)
        {
            OnError?.Invoke($"WebSocketException: {wex.Message}");
        }
        catch (Exception ex)
        {
            OnError?.Invoke($"Exception: {ex.Message}");
        }
    }
    
    public async void Disconnect()
    {
        try
        {
            isConnected = false;
            if (cancellationTokenSource != null)
            {
                cancellationTokenSource.Cancel();
            }
            
            if (webSocket != null && webSocket.State == WebSocketState.Open)
            {
                await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Disconnecting", CancellationToken.None);
            }
            webSocket?.Dispose();
            webSocket = null;
            
            OnDisconnected?.Invoke();
        }
        catch (WebSocketException wex)
        {
            OnError?.Invoke($"WebSocketException: {wex.Message}");
        }
        catch (Exception ex)
        {
            OnError?.Invoke($"Exception: {ex.Message}");
        }
    }
    
    public async void SendMessage(string message)
    {
        if (!isConnected || webSocket == null || webSocket.State != WebSocketState.Open)
            return;
            
        try
        {
            byte[] buffer = Encoding.UTF8.GetBytes(message);
            await webSocket.SendAsync(new ArraySegment<byte>(buffer), WebSocketMessageType.Text, true, cancellationTokenSource.Token);
        }
        catch (WebSocketException wex)
        {
            OnError?.Invoke($"WebSocketException: {wex.Message}");
        }
        catch (Exception ex)
        {
            OnError?.Invoke($"Exception: {ex.Message}");
        }
    }
    
    private async Task ReceiveMessages()
    {
        byte[] buffer = new byte[64 * 1024];
        
        while (isConnected && webSocket.State == WebSocketState.Open)
        {
            try
            {
                WebSocketReceiveResult result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationTokenSource.Token);
                
                if (result.MessageType == WebSocketMessageType.Text)
                {
                    string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    OnMessageReceived?.Invoke(message);
                }
                else if (result.MessageType == WebSocketMessageType.Close)
                {
                    isConnected = false;
                    OnDisconnected?.Invoke();
                    break;
                }
            }
            catch (WebSocketException wex)
            {
                OnError?.Invoke($"WebSocketException: {wex.Message}");
                break;
            }
            catch (Exception ex)
            {
                OnError?.Invoke($"Exception: {ex.Message}");
                break;
            }
        }
    }
    
    public bool IsConnected()
    {
        return isConnected && webSocket != null && webSocket.State == WebSocketState.Open;
    }
}
