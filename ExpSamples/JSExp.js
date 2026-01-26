/**
 * LaunchDarkly A/B Testing Implementation Patterns for Financial Services
 * 
 * This sample demonstrates enterprise-grade A/B testing patterns including:
 * - Multi-variant testing with proper fallbacks
 * - Conversion tracking and metrics collection
 * - User segmentation and progressive rollouts
 * - Error handling and observability
 * - Financial services specific use cases
 */

// Initialize LaunchDarkly Client
import LDClient from 'launchdarkly-js-client-sdk';

class FinancialABTestingService {
    constructor(clientSideId, userId, userAttributes = {}) {
        this.ldClient = null;
        this.userId = userId;
        this.isInitialized = false;
        this.metrics = new Map();
        
        // Standard user context for financial services
        this.userContext = {
            key: userId,
            name: userAttributes.name || 'Anonymous',
            email: userAttributes.email,
            custom: {
                accountType: userAttributes.accountType || 'retail',
                riskProfile: userAttributes.riskProfile || 'moderate',
                customerSegment: userAttributes.customerSegment || 'standard',
                totalAssets: userAttributes.totalAssets || 0,
                accountTenure: userAttributes.accountTenure || 0,
                lastLoginDays: userAttributes.lastLoginDays || 0,
                platform: userAttributes.platform || 'web'
            }
        };
        
        this.initializeLD(clientSideId);
    }

    async initializeLD(clientSideId) {
        try {
            this.ldClient = LDClient.initialize(clientSideId, this.userContext);
            
            await this.ldClient.waitForInitialization();
            this.isInitialized = true;
            console.log('LaunchDarkly initialized successfully');
            
            // Track initialization event
            this.trackEvent('LD_SDK_Initialized', {
                platform: this.userContext.custom.platform,
                accountType: this.userContext.custom.accountType
            });
            
        } catch (error) {
            console.error('Failed to initialize LaunchDarkly:', error);
            this.isInitialized = false;
        }
    }

    /**
     * PATTERN 1: Investment Dashboard Layout A/B Test
     * Tests different dashboard layouts for investment performance display
     */
    async getInvestmentDashboardVariant() {
        const flagKey = 'investment-dashboard-layout';
        const defaultVariant = 'classic';
        
        try {
            if (!this.isInitialized) {
                console.warn('LD not initialized, using default variant');
                return defaultVariant;
            }

            const variant = this.ldClient.variation(flagKey, defaultVariant);
            
            // Track exposure for this experiment
            this.trackEvent('experiment_exposure', {
                experimentName: 'investment_dashboard_layout',
                variant: variant,
                userSegment: this.userContext.custom.customerSegment,
                totalAssets: this.userContext.custom.totalAssets
            });

            return variant;
            
        } catch (error) {
            console.error(`Error getting variant for ${flagKey}:`, error);
            return defaultVariant;
        }
    }

    /**
     * PATTERN 2: Loan Application Flow with Progressive Rollout
     * Tests a streamlined loan application process
     */
    async getLoanApplicationFlow() {
        const flagKey = 'streamlined-loan-application';
        const defaultFlow = 'traditional';
        
        try {
            const flowType = this.ldClient.variation(flagKey, defaultFlow);
            
            // Different flows based on user risk profile
            const flowConfig = {
                traditional: {
                    steps: ['personal_info', 'financial_info', 'documentation', 'review', 'submit'],
                    estimatedTime: '15-20 minutes',
                    preApprovalEnabled: false
                },
                streamlined: {
                    steps: ['quick_info', 'instant_decision', 'documentation'],
                    estimatedTime: '5-8 minutes',
                    preApprovalEnabled: true
                },
                premium: {
                    steps: ['priority_info', 'instant_approval'],
                    estimatedTime: '2-3 minutes',
                    preApprovalEnabled: true,
                    dedicatedSupport: true
                }
            };

            this.trackEvent('loan_flow_assignment', {
                flowType: flowType,
                riskProfile: this.userContext.custom.riskProfile,
                accountTenure: this.userContext.custom.accountTenure
            });

            return flowConfig[flowType] || flowConfig[defaultFlow];
            
        } catch (error) {
            console.error('Error getting loan application flow:', error);
            return flowConfig[defaultFlow];
        }
    }

    /**
     * PATTERN 3: Dynamic Interest Rate Display
     * A/B tests different ways of presenting interest rates and promotions
     */
    async getInterestRateDisplay(productType) {
        const flagKey = 'interest-rate-display-format';
        const defaultFormat = 'standard';
        
        try {
            const displayFormat = this.ldClient.variation(flagKey, defaultFormat);
            
            const formatConfig = {
                standard: {
                    showAPR: true,
                    showMonthlyPayment: false,
                    highlightPromotions: false,
                    comparisonMode: false
                },
                enhanced: {
                    showAPR: true,
                    showMonthlyPayment: true,
                    highlightPromotions: true,
                    comparisonMode: false,
                    showSavingsCalculator: true
                },
                competitive: {
                    showAPR: true,
                    showMonthlyPayment: true,
                    highlightPromotions: true,
                    comparisonMode: true,
                    showMarketComparison: true
                }
            };

            this.trackEvent('rate_display_shown', {
                productType: productType,
                displayFormat: displayFormat,
                customerSegment: this.userContext.custom.customerSegment
            });

            return formatConfig[displayFormat] || formatConfig[defaultFormat];
            
        } catch (error) {
            console.error('Error getting interest rate display format:', error);
            return formatConfig[defaultFormat];
        }
    }

    /**
     * PATTERN 4: Risk-Based Feature Access
     * Uses feature flags with user targeting for risk-sensitive features
     */
    async getRiskBasedFeatures() {
        const features = {};
        
        try {
            // High-risk trading features
            features.optionsTrading = this.ldClient.variation('enable-options-trading', false);
            features.marginTrading = this.ldClient.variation('enable-margin-trading', false);
            features.cryptoTrading = this.ldClient.variation('enable-crypto-trading', false);
            
            // Investment advisory features
            features.roboAdvisor = this.ldClient.variation('enable-robo-advisor', true);
            features.humanAdvisor = this.ldClient.variation('enable-human-advisor-access', false);
            
            // Premium features
            features.realTimeData = this.ldClient.variation('real-time-market-data', false);
            features.advancedAnalytics = this.ldClient.variation('advanced-analytics', false);

            this.trackEvent('feature_access_evaluation', {
                features: Object.keys(features).filter(key => features[key]),
                riskProfile: this.userContext.custom.riskProfile,
                accountType: this.userContext.custom.accountType
            });

            return features;
            
        } catch (error) {
            console.error('Error evaluating risk-based features:', error);
            return {
                optionsTrading: false,
                marginTrading: false,
                cryptoTrading: false,
                roboAdvisor: true,
                humanAdvisor: false,
                realTimeData: false,
                advancedAnalytics: false
            };
        }
    }

    /**
     * PATTERN 5: Conversion Tracking and Metrics
     * Tracks key financial services conversion events
     */
    trackConversion(conversionType, metadata = {}) {
        const conversionEvent = {
            eventType: 'conversion',
            conversionType: conversionType,
            timestamp: new Date().toISOString(),
            userId: this.userId,
            metadata: {
                ...metadata,
                customerSegment: this.userContext.custom.customerSegment,
                platform: this.userContext.custom.platform
            }
        };

        // Track with LaunchDarkly
        if (this.isInitialized) {
            this.ldClient.track(conversionType, this.userContext, metadata);
        }

        // Store locally for batch reporting
        if (!this.metrics.has('conversions')) {
            this.metrics.set('conversions', []);
        }
        this.metrics.get('conversions').push(conversionEvent);

        console.log(`Conversion tracked: ${conversionType}`, conversionEvent);
    }

    /**
     * PATTERN 6: A/B Test Result Analysis Helper
     * Provides utilities for analyzing test performance
     */
    async analyzeExperimentPerformance(experimentName, timeRangeHours = 24) {
        try {
            const conversions = this.metrics.get('conversions') || [];
            const experimentConversions = conversions.filter(c => 
                c.metadata.experimentName === experimentName &&
                new Date(c.timestamp) > Date.now() - (timeRangeHours * 3600 * 1000)
            );

            const analysis = {
                totalConversions: experimentConversions.length,
                conversionsByVariant: {},
                averageTimeToConversion: 0,
                topConvertingSegments: {}
            };

            // Group by variant
            experimentConversions.forEach(conversion => {
                const variant = conversion.metadata.variant || 'unknown';
                if (!analysis.conversionsByVariant[variant]) {
                    analysis.conversionsByVariant[variant] = 0;
                }
                analysis.conversionsByVariant[variant]++;
            });

            return analysis;
            
        } catch (error) {
            console.error('Error analyzing experiment performance:', error);
            return null;
        }
    }

    /**
     * Helper method for tracking events
     */
    trackEvent(eventName, properties = {}) {
        try {
            if (this.isInitialized) {
                this.ldClient.track(eventName, this.userContext, properties);
            }
            
            console.log(`Event tracked: ${eventName}`, properties);
        } catch (error) {
            console.error(`Error tracking event ${eventName}:`, error);
        }
    }

    /**
     * Cleanup method
     */
    cleanup() {
        if (this.ldClient) {
            this.ldClient.close();
        }
    }
}

// Usage Examples for Financial Services A/B Testing

class FinancialUIController {
    constructor(abTestingService) {
        this.abTesting = abTestingService;
    }

    async renderInvestmentDashboard() {
        const variant = await this.abTesting.getInvestmentDashboardVariant();
        
        switch (variant) {
            case 'modern':
                this.renderModernDashboard();
                break;
            case 'compact':
                this.renderCompactDashboard();
                break;
            default:
                this.renderClassicDashboard();
        }

        // Track dashboard view
        this.abTesting.trackEvent('dashboard_viewed', {
            variant: variant,
            viewTimestamp: Date.now()
        });
    }

    async handleLoanApplicationStart() {
        const flowConfig = await this.abTesting.getLoanApplicationFlow();
        
        // Configure the application flow based on A/B test
        this.setupLoanFlow(flowConfig);
        
        // Track the start of loan application
        this.abTesting.trackEvent('loan_application_started', {
            flowType: flowConfig.steps.length > 3 ? 'traditional' : 'streamlined',
            estimatedTime: flowConfig.estimatedTime
        });
    }

    async displayProductRates(productType) {
        const displayConfig = await this.abTesting.getInterestRateDisplay(productType);
        
        // Render rate display based on experiment variant
        this.renderRateDisplay(productType, displayConfig);
        
        // Track rate display interaction
        this.abTesting.trackEvent('rate_display_interaction', {
            productType: productType,
            displayFormat: displayConfig.comparisonMode ? 'competitive' : 'standard'
        });
    }

    // Conversion tracking examples
    handleAccountOpening(accountType) {
        this.abTesting.trackConversion('account_opened', {
            accountType: accountType,
            source: 'web_application'
        });
    }

    handleLoanCompletion(loanAmount, loanType) {
        this.abTesting.trackConversion('loan_completed', {
            loanAmount: loanAmount,
            loanType: loanType,
            completionTime: Date.now()
        });
    }

    handleInvestmentPurchase(investmentType, amount) {
        this.abTesting.trackConversion('investment_purchase', {
            investmentType: investmentType,
            amount: amount,
            purchaseDate: new Date().toISOString()
        });
    }

    // Placeholder rendering methods
    renderModernDashboard() { console.log('Rendering modern dashboard...'); }
    renderCompactDashboard() { console.log('Rendering compact dashboard...'); }
    renderClassicDashboard() { console.log('Rendering classic dashboard...'); }
    setupLoanFlow(config) { console.log('Setting up loan flow:', config); }
    renderRateDisplay(productType, config) { console.log('Rendering rate display:', productType, config); }
}

// Example initialization and usage
export default class FinancialABTestingExample {
    static async initialize(clientSideId, userId, userAttributes) {
        // Initialize the A/B testing service
        const abTesting = new FinancialABTestingService(clientSideId, userId, userAttributes);
        
        // Wait for initialization
        await new Promise(resolve => {
            const checkInit = () => {
                if (abTesting.isInitialized) {
                    resolve();
                } else {
                    setTimeout(checkInit, 100);
                }
            };
            checkInit();
        });

        // Initialize UI controller
        const uiController = new FinancialUIController(abTesting);

        // Example usage flow
        await uiController.renderInvestmentDashboard();
        
        // Simulate user interactions
        setTimeout(async () => {
            await uiController.displayProductRates('mortgage');
            uiController.handleAccountOpening('checking');
        }, 2000);

        return { abTesting, uiController };
    }
}

/* 
Example initialization:
const { abTesting, uiController } = await FinancialABTestingExample.initialize(
    'your-launchdarkly-client-side-id',
    'user-123',
    {
        name: 'John Smith',
        email: 'john.smith@email.com',
        accountType: 'premium',
        riskProfile: 'aggressive',
        customerSegment: 'high_value',
        totalAssets: 500000,
        accountTenure: 36,
        lastLoginDays: 1,
        platform: 'web'
    }
);
*/
