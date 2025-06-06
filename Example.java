import com.launchdarkly.sdk.*;
import com.launchdarkly.sdk.server.*;

public class Example {
    public static void main(String[] args) {
        // Initialize the LDClient with your SDK key
        LDClient client = new LDClient("your-sdk-key");

        role = getSystemRole();

        try {
            // Create a context with a role
            LDContext context = LDContext.builder("user-key-123")
                .set("role", role)
                .build();

            // Evaluate the flag
            boolean accessGranted = client.boolVariation("accessGranted", context, false);

            // Print the result
            if (accessGranted) {
                System.out.println("Access is granted for role: " + context.getValue("role"));
                useUpdatedURL()
            } else {
                System.out.println("Access is denied for role: " + context.getValue("role"));
                useOldURL()
            }

        } finally {
            // Always close the client when you're done
            client.close();
        }
    }
} 