package main

import (
	"encoding/json"
	"html/template"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/launchdarkly/go-sdk-common/v3/ldcontext"
	"github.com/launchdarkly/go-server-sdk/ldai"
	ld "github.com/launchdarkly/go-server-sdk/v7"
)

var (
	configMutex   sync.RWMutex
	currentConfig ldai.Config
	ldClient      *ld.LDClient
	aiClient      *ldai.Client
)

func updateConfig(config ldai.Config) {
	configMutex.Lock()
	defer configMutex.Unlock()

	// Log the configuration for debugging
	log.Printf("config: %+v", &config)

	currentConfig = config
	log.Println()
	log.Printf("Current messages: %+v", currentConfig.Messages())
	maxTokens, _ := currentConfig.ModelParam("maxTokens")
	log.Printf("Max tokens: %+v", maxTokens)

}

type ConfigView struct {
	ModelName   string
	Temperature float64
	MaxTokens   int
}

func handleConfig(w http.ResponseWriter, r *http.Request) {
	configMutex.RLock()
	defer configMutex.RUnlock()

	if r.Header.Get("Accept") == "application/json" {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(currentConfig)
		return
	}

	view := ConfigView{
		ModelName:   "default-model", // Default value
		Temperature: 0.7,             // Default value
		MaxTokens:   1000,            // Default value
	}

	// Override with actual config values if present
	if name := currentConfig.ModelName(); name != "" {
		view.ModelName = name
	}
	if v, ok := currentConfig.ModelParam("temperature"); ok {
		view.Temperature = v.Float64Value()
	}
	if v, ok := currentConfig.ModelParam("maxTokens"); ok {
		view.MaxTokens = int(v.IntValue())
	}

	tmpl := `
<!DOCTYPE html>
<html>
<head>
    <title>Configuration State</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .config-container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .config-item {
            margin-bottom: 15px;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        .config-label {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .config-value {
            color: #666;
            font-family: monospace;
            background-color: #f8f9fa;
            padding: 5px;
            border-radius: 4px;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 20px;
        }
        .last-updated {
            color: #666;
            font-size: 0.9em;
            text-align: right;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="config-container">
        <h1>Configuration State</h1>
        <div class="config-item">
            <div class="config-label">Model Name:</div>
            <div class="config-value">{{.ModelName}}</div>
        </div>
        <div class="config-item">
            <div class="config-label">Temperature:</div>
            <div class="config-value">{{.Temperature}}</div>
        </div>
        <div class="config-item">
            <div class="config-label">Max Tokens:</div>
            <div class="config-value">{{.MaxTokens}}</div>
        </div>
        <div class="last-updated">
            Auto-refreshes every 5 seconds
        </div>
        <script>
            setTimeout(function() {
                window.location.reload();
            }, 5000);
        </script>
    </div>
</body>
</html>`

	t, err := template.New("config").Parse(tmpl)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	err = t.Execute(w, view)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

func main() {
	// Set up HTTP server
	http.HandleFunc("/", handleConfig)

	var err error
	ldClient, err := ld.MakeClient("sdk-1d89b872-46ff-4155-b86d-f1a067bdcf5e", 5*time.Second)
	if err != nil {
		log.Fatalf("Failed to create LaunchDarkly client: %v", err)
	}
	defer ldClient.Close()

	aiClient, err := ldai.NewClient(ldClient)
	if err != nil {
		log.Fatalf("Failed to create AI client: %v", err)
	}

	// Start periodic config updates
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				// Get fresh config on each tick
				newConfig, _ := aiClient.Config("ai-config--ai-new-model-chatbot", ldcontext.New("user-key"), ldai.Disabled(), nil)
				updateConfig(newConfig)
			}
		}
	}()

	log.Println("Starting web server on http://localhost:8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatalf("Failed to start web server: %v", err)
	}
}
