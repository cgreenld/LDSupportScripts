# LaunchDarkly Dual SDK Flask Demo

A Flask app demonstrating both **server-side** and **client-side** LaunchDarkly SDKs for comprehensive feature flag management.

## 🚀 Features

- **🖥️ Server-Side SDK**: Flag evaluation on the Flask backend
- **🌐 Client-Side SDK**: Real-time flag evaluation in the browser  
- **📊 Live Monitoring**: Instant flag updates without page refresh
- **🔄 Change Tracking**: Visual indicators and change log for flag updates
- **📡 Dual Evaluation**: Compare server-side vs client-side flag results

## 📋 Pages

- **`/`** - Home page with SDK status indicators
- **`/sample`** - Server-side flag demonstrations
- **`/live-flags`** - **Real-time client-side flag monitoring** 🔥
- **`/api/all-flags`** - Server-side JSON API endpoint
- **`/health`** - Health check with SDK status

## ⚙️ Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure LaunchDarkly Keys
You need **both** server-side and client-side SDK keys:

```bash
# Server-side SDK key (starts with "sdk-")
export LD_SERVER_SDK_KEY="sdk-your-server-key-here"

# Client-side SDK key (different from server key)
export LD_CLIENT_SDK_KEY="your-client-key-here"
```

### 3. Run the Application
```bash
python app.py
```

### 4. Visit the App
Open `http://localhost:5000` in your browser

## 🎯 SDK Comparison

| Feature | Server-Side SDK | Client-Side SDK |
|---------|-----------------|-----------------|
| **Location** | Flask Backend | Browser JavaScript |
| **Evaluation** | On page load | Real-time |
| **Updates** | Requires refresh | Instant |
| **Security** | Full access | Limited to client flags |
| **Performance** | Server resources | Browser resources |
| **Use Case** | Server logic | UI/UX features |

## 🔧 Feature Flags Used

Create these boolean flags in your LaunchDarkly project:

- `show-welcome-banner`
- `new-ui-enabled` 
- `beta-features`
- `premium-content`
- `dark-mode`
- `maintenance-mode`
- `feature-a`
- `feature-b`
- `debug-mode`
- `analytics-enabled`

## 🎮 Try It Out

1. **Create flags** in your LaunchDarkly dashboard
2. **Toggle flags** while viewing `/live-flags`
3. **Watch real-time updates** without page refresh! 
4. **Compare** server-side (`/sample`) vs client-side (`/live-flags`) evaluation

## 📱 Real-Time Features

The `/live-flags` page showcases:
- ⚡ **Instant updates** when flags change
- 🎨 **Visual highlights** for changed flags  
- 📝 **Change log** with timestamps
- ⏸️ **Pause/resume** real-time updates
- 🔄 **Manual refresh** option

## 🛡️ Security Notes

- Server-side keys have full project access
- Client-side keys are restricted to client-side flags only
- Never expose server-side keys in browser code
- Use environment variables for all keys