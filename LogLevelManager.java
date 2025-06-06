import com.launchdarkly.sdk.*;
import com.launchdarkly.sdk.server.*;

public class LogLevelManager {
    private static final String LOG_LEVEL_FLAG = "log-level";
    private final LDClient client;

    public enum LogLevel {
        DEBUG,
        INFO,
        ERROR
    }

    public LogLevelManager(String sdkKey) {
        this.client = new LDClient(sdkKey);
    }

    public void log(String message, LDContext context) {
        // Get the log level from LaunchDarkly
        String logLevelValue = client.stringVariation(LOG_LEVEL_FLAG, context, "INFO");
        LogLevel currentLevel = LogLevel.valueOf(logLevelValue);

        // Log based on the current level
        switch (currentLevel) {
            case DEBUG:
                System.out.println("[DEBUG] " + message);
                break;
            case INFO:
                System.out.println("[INFO] " + message);
                break;
            case ERROR:
                System.err.println("[ERROR] " + message);
                break;
        }
    }

    public void close() {
        client.close();
    }

    // Example usage
    public static void main(String[] args) {
        String sdkKey = "your-sdk-key"; // Replace with your actual SDK key
        LogLevelManager logger = new LogLevelManager(sdkKey);

        // Create a context for the user
        LDContext context = LDContext.builder("user-key")
                .kind("user")
                .build();

        // Example log messages
        logger.log("This is a debug message", context);
        logger.log("This is an info message", context);
        logger.log("This is an error message", context);

        logger.close();
    }
} 