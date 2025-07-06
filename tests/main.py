from testBuilder import *


if __name__ == "__main__":
    try:
        # Replace with your actual Lambda API Gateway URL
        LAMBDA_URL = "https://3ercr9p006.execute-api.us-east-1.amazonaws.com/test"
        LAMBDA_URL = "https://3rkiwejlxdwtfko6zigftlwz4e0fydfu.lambda-url.us-east-1.on.aws/"
        
        # Test configuration
        test_config = (
            TestBuilder()
            .with_counts(small=5, medium=3, large=1)
            .with_k_range(k_min=2, k_max=8)
            .with_concurrent_requests(3)
            .with_url(LAMBDA_URL)
            .build()
        )
        
        test_config.run_tests()
        
    except ValueError as e:
        logger.error(f"❌ Error creating test: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")