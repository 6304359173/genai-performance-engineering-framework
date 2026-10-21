pipeline {

    agent any

    environment {

        // =========================================================
        // PYTHON
        // =========================================================
        PYTHON_EXE = 'C:\\Users\\LENOVO\\AppData\\Local\\Programs\\Python\\Python314\\python.exe'

        // =========================================================
        // JMETER 5.6.3
        // =========================================================
        JMETER_CMD = 'C:\\Loadmagic\\apache-jmeter-5.6.3\\apache-jmeter-5.6.3\\bin\\jmeter.bat'

        // =========================================================
        // KUBERNETES
        // =========================================================
        KUBECONFIG = 'C:\\Users\\LENOVO\\.kube\\config'

        K8S_CONTEXT = 'docker-desktop'

        K8S_SERVICE = 'ai-perf-order-service'

        K8S_SERVICE_PORT = '3002'

        LOCAL_PORT = '3003'

        // =========================================================
        // JMETER PARAMETERS
        // =========================================================
        TEST_USERS = '10'

        RAMP_UP = '30'

        DURATION = '60'

        // =========================================================
        // PROJECT FILES
        // =========================================================
        JMX_FILE = 'scripts\\ai_perf_test.jmx'

        JTL_FILE = 'scripts\\results.jtl'

        METRICS_FILE = 'python-engine\\metrics.json'

        // =========================================================
        // MCP
        // =========================================================
        MCP_CLIENT = 'mcp-server\\mcp_client.py'

        MCP_EVIDENCE = 'ai-engine\\mcp_rca_evidence.json'

        // =========================================================
        // AI RCA
        // =========================================================
        LLM_CLIENT = 'ai-engine\\llm_client.py'

        RCA_PROMPT = 'ai-engine\\ai_rca_prompt_from_mcp.txt'

        MOCK_RCA = 'ai-engine\\mock_ai_rca.py'

        RCA_REPORT = 'ai-engine\\ai_rca_report.md'
    }


    stages {

        // =========================================================
        // 1. CHECKOUT
        // =========================================================

        stage('Checkout') {

            steps {

                echo '========================================'
                echo 'CHECKOUT'
                echo '========================================'

                checkout scm

                bat '''
                    echo.
                    echo ===== WORKSPACE =====
                    cd

                    echo.
                    echo ===== GIT VERSION =====
                    git --version

                    echo.
                    echo ===== COMMIT =====
                    git rev-parse --short HEAD

                    echo.
                    echo ===== BRANCH =====
                    git branch --show-current
                '''
            }
        }


        // =========================================================
        // 2. ENVIRONMENT CHECK
        // =========================================================

        stage('Environment Check') {

            steps {

                echo '========================================'
                echo 'ENVIRONMENT CHECK'
                echo '========================================'

                bat '''
                    echo.
                    echo ===== JAVA =====
                    java -version

                    echo.
                    echo ===== PYTHON =====
                    "%PYTHON_EXE%" --version

                    echo.
                    echo ===== NODE =====
                    node --version

                    echo.
                    echo ===== NPM =====
                    npm --version

                    echo.
                    echo ===== DOCKER =====
                    docker --version

                    echo.
                    echo ===== KUBECTL =====
                    kubectl version --client

                    echo.
                    echo ===== JMETER =====
                    "%JMETER_CMD%" --version
                '''
            }
        }


        // =========================================================
        // 3. VALIDATE FILES
        // =========================================================

        stage('Validate Project') {

            steps {

                echo '========================================'
                echo 'VALIDATE PROJECT'
                echo '========================================'

                bat '''
                    echo Checking project files...

                    if not exist "%JMX_FILE%" (
                        echo ERROR: JMeter file not found:
                        echo %JMX_FILE%
                        exit /b 1
                    )

                    if not exist "python-engine\\analyzer.py" (
                        echo ERROR: analyzer.py not found
                        exit /b 1
                    )

                    if not exist "mcp-server\\performance_mcp.py" (
                        echo ERROR: performance_mcp.py not found
                        exit /b 1
                    )

                    if not exist "%MCP_CLIENT%" (
                        echo ERROR: mcp_client.py not found
                        exit /b 1
                    )

                    if not exist "%LLM_CLIENT%" (
                        echo ERROR: llm_client.py not found
                        exit /b 1
                    )

                    echo.
                    echo All required files exist.
                '''
            }
        }


        // =========================================================
        // 4. KUBERNETES CHECK
        // =========================================================

        stage('Kubernetes Check') {

            steps {

                echo '========================================'
                echo 'KUBERNETES CHECK'
                echo '========================================'

                bat '''
                    set KUBECONFIG=%KUBECONFIG%

                    echo.
                    echo ===== CURRENT CONTEXT =====
                    kubectl config current-context

                    echo.
                    echo ===== NODES =====
                    kubectl get nodes

                    echo.
                    echo ===== APPLICATION PODS =====
                    kubectl get pods -l app=ai-perf-order-service

                    echo.
                    echo ===== SERVICE =====
                    kubectl get service %K8S_SERVICE%

                    echo.
                    echo ===== ENDPOINTS =====
                    kubectl get endpoints %K8S_SERVICE%
                '''
            }
        }


        // =========================================================
        // 5. START PORT FORWARD
        // =========================================================

        stage('Start Kubernetes Port Forward') {

            steps {

                echo '========================================'
                echo 'START KUBERNETES PORT FORWARD'
                echo '========================================'

                bat '''
                    set KUBECONFIG=%KUBECONFIG%

                    echo.
                    echo ===== CHECK PORT 3003 =====

                    netstat -ano | findstr :3003

                    echo.
                    echo ===== STOP PROCESS USING PORT 3003 =====

                    for /f "tokens=5" %%A in ('netstat -ano ^| findstr :3003 ^| findstr LISTENING') do (
                        echo Stopping PID %%A
                        taskkill /PID %%A /T /F >nul 2>&1
                    )

                    timeout /t 2 /nobreak >nul

                    echo.
                    echo ===== CLEAN OLD LOG =====

                    if exist k8s-port-forward.log (
                        del /f /q k8s-port-forward.log
                    )

                    echo.
                    echo ===== START PORT FORWARD =====

                    start "" /b cmd /c "kubectl --kubeconfig C:\\Users\\LENOVO\\.kube\\config port-forward service/ai-perf-order-service 3003:3002 > k8s-port-forward.log 2>&1"

                    echo.
                    echo Port-forward process started.

                    echo.
                    echo ===== WAIT =====

                    timeout /t 5 /nobreak >nul

                    echo.
                    echo ===== PORT STATUS =====

                    netstat -ano | findstr :3003

                    echo.
                    echo ===== HEALTH CHECK =====

                    curl.exe -s http://127.0.0.1:3003/health

                    if errorlevel 1 (
                        echo.
                        echo ERROR: Application health check failed.

                        echo.
                        echo ===== PORT FORWARD LOG =====

                        if exist k8s-port-forward.log (
                            type k8s-port-forward.log
                        )

                        exit /b 1
                    )

                    echo.
                    echo.
                    echo PORT FORWARD READY
                '''
            }
        }


        // =========================================================
        // 6. APPLICATION VALIDATION
        // =========================================================

        stage('Application Validation') {

            steps {

                echo '========================================'
                echo 'APPLICATION VALIDATION'
                echo '========================================'

                bat '''
                    echo.
                    echo ===== HEALTH =====

                    curl.exe -s http://127.0.0.1:3003/health

                    if errorlevel 1 (
                        echo ERROR: Health endpoint failed
                        exit /b 1
                    )

                    echo.
                    echo.
                    echo ===== PRODUCTS =====

                    curl.exe -s http://127.0.0.1:3003/products

                    if errorlevel 1 (
                        echo ERROR: Products endpoint failed
                        exit /b 1
                    )

                    echo.
                    echo.
                    echo Application validation successful.
                '''
            }
        }


        // =========================================================
        // 7. KUBERNETES METRICS
        // =========================================================

        stage('Kubernetes Metrics') {

            steps {

                echo '========================================'
                echo 'KUBERNETES METRICS'
                echo '========================================'

                bat '''
                    set KUBECONFIG=%KUBECONFIG%

                    echo.
                    echo ===== NODE METRICS =====

                    kubectl top nodes

                    if errorlevel 1 (
                        echo ERROR: kubectl top nodes failed
                        exit /b 1
                    )

                    echo.
                    echo ===== POD METRICS =====

                    kubectl top pods

                    if errorlevel 1 (
                        echo ERROR: kubectl top pods failed
                        exit /b 1
                    )

                    echo.
                    echo ===== APPLICATION POD METRICS =====

                    kubectl top pods -l app=ai-perf-order-service
                '''
            }
        }


        // =========================================================
        // 8. RUN JMETER
        // =========================================================

        stage('Run JMeter') {

            steps {

                echo '========================================'
                echo 'RUN JMETER PERFORMANCE TEST'
                echo '========================================'

                bat '''
                    echo.
                    echo ===== JMETER VERSION =====

                    "%JMETER_CMD%" --version

                    echo.
                    echo ===== TEST CONFIGURATION =====

                    echo Users    = %TEST_USERS%
                    echo Ramp Up  = %RAMP_UP%
                    echo Duration = %DURATION%

                    echo.
                    echo ===== TARGET =====

                    echo http://localhost:3003

                    echo.
                    echo ===== DELETE OLD JTL =====

                    if exist "%JTL_FILE%" (
                        del /f /q "%JTL_FILE%"
                    )

                    echo.
                    echo ===== START JMETER =====

                    "%JMETER_CMD%" -n ^
                        -JTEST_USERS=%TEST_USERS% ^
                        -JRAMP_UP=%RAMP_UP% ^
                        -JDURATION=%DURATION% ^
                        -t "%JMX_FILE%" ^
                        -l "%JTL_FILE%"

                    if errorlevel 1 (
                        echo.
                        echo ERROR: JMeter execution failed.
                        exit /b 1
                    )

                    echo.
                    echo ===== JMETER COMPLETED =====

                    if not exist "%JTL_FILE%" (
                        echo ERROR: JTL file was not created.
                        exit /b 1
                    )

                    echo.
                    echo ===== RESULT FILE =====

                    dir "%JTL_FILE%"
                '''
            }
        }


        // =========================================================
        // 9. PYTHON ANALYSIS
        // =========================================================

        stage('Performance Analysis') {

            steps {

                echo '========================================'
                echo 'PYTHON PERFORMANCE ANALYSIS'
                echo '========================================'

                bat '''
                    echo.
                    echo ===== RUN ANALYZER =====

                    "%PYTHON_EXE%" python-engine\\analyzer.py

                    if errorlevel 1 (
                        echo ERROR: analyzer.py failed
                        exit /b 1
                    )

                    echo.
                    echo ===== VERIFY METRICS =====

                    if not exist "%METRICS_FILE%" (
                        echo ERROR: metrics.json was not created
                        exit /b 1
                    )

                    echo.
                    echo ===== PERFORMANCE METRICS =====

                    type "%METRICS_FILE%"
                '''
            }
        }


        // =========================================================
        // 10. MCP
        // =========================================================

        stage('MCP Evidence') {

            steps {

                echo '========================================'
                echo 'MCP PERFORMANCE EVIDENCE'
                echo '========================================'

                bat '''
                    set KUBECONFIG=%KUBECONFIG%

                    echo.
                    echo ===== KUBERNETES CONTEXT =====

                    kubectl config current-context

                    echo.
                    echo ===== KUBERNETES METRICS =====

                    kubectl top nodes

                    echo.
                    echo.

                    kubectl top pods

                    echo.
                    echo ===== RUN MCP CLIENT =====

                   	"%PYTHON_EXE%" "%MCP_CLIENT%"

					if errorlevel 1 (
						echo ERROR: MCP client failed
						exit /b 1
					)

					echo.
					echo ===== VERIFY MCP EVIDENCE =====

					if not exist "%MCP_EVIDENCE%" (
						echo ERROR: MCP evidence file was not created
						exit /b 1
					)

					echo.
					echo ===== MCP EVIDENCE =====

					type "%MCP_EVIDENCE%"
                '''
            }
        }


        // =========================================================
        // 11. AI RCA
        // =========================================================

        stage('AI RCA') {

            steps {

                echo '========================================'
                echo 'AI PERFORMANCE RCA'
                echo '========================================'

                bat '''
                    echo.
                    echo ===== RUN LLM CLIENT =====

                    "%PYTHON_EXE%" "%LLM_CLIENT%"

                    echo.
                    echo ===== RCA PROMPT =====

                    if exist "%RCA_PROMPT%" (
                        type "%RCA_PROMPT%"
                    ) else (
                        echo RCA prompt was not generated.
                    )
                '''
            }
        }


        // =========================================================
        // 12. RCA REPORT
        // =========================================================

        stage('Generate RCA Report') {

            steps {

                echo '========================================'
                echo 'GENERATE RCA REPORT'
                echo '========================================'

                bat '''
                    if exist "%MOCK_RCA%" (

                        echo.
                        echo ===== RUN MOCK RCA =====

                        "%PYTHON_EXE%" "%MOCK_RCA%"

                        if errorlevel 1 (
                            echo WARNING: RCA generation returned an error
                        )

                    ) else (

                        echo mock_ai_rca.py not found
                        echo Skipping mock RCA generation

                    )

                    echo.
                    echo ===== RCA REPORT =====

                    if exist "%RCA_REPORT%" (
                        type "%RCA_REPORT%"
                    ) else (
                        echo RCA report not available
                    )
                '''
            }
        }


        // =========================================================
        // 13. PREPARE ARTIFACTS
        // =========================================================

        stage('Prepare Artifacts') {

            steps {

                echo '========================================'
                echo 'PREPARE JENKINS ARTIFACTS'
                echo '========================================'

                bat '''
                    if not exist results (
                        mkdir results
                    )

                    echo.
                    echo ===== COPY JTL =====

                    if exist "%JTL_FILE%" (
                        copy /Y "%JTL_FILE%" "results\\results.jtl"
                    )

                    echo.
                    echo ===== COPY METRICS =====

                    if exist "%METRICS_FILE%" (
                        copy /Y "%METRICS_FILE%" "results\\metrics.json"
                    )

                    echo.
                    echo ===== COPY MCP EVIDENCE =====

                    if exist "%MCP_EVIDENCE%" (
                        copy /Y "%MCP_EVIDENCE%" "results\\mcp_rca_evidence.json"
                    )

                    echo.
                    echo ===== COPY RCA PROMPT =====

                    if exist "%RCA_PROMPT%" (
                        copy /Y "%RCA_PROMPT%" "results\\ai_rca_prompt_from_mcp.txt"
                    )

                    echo.
                    echo ===== COPY RCA REPORT =====

                    if exist "%RCA_REPORT%" (
                        copy /Y "%RCA_REPORT%" "results\\ai_rca_report.md"
                    )

                    echo.
                    echo ===== RESULTS =====

                    dir results
                '''
            }
        }
    }


    // =============================================================
    // POST
    // =============================================================

    post {

        always {

            echo '========================================'
            echo 'CLEANUP'
            echo '========================================'

            bat '''
                echo.
                echo ===== STOP PORT FORWARD =====

                for /f "tokens=5" %%A in ('netstat -ano ^| findstr :3003 ^| findstr LISTENING') do (
                    echo Stopping PID %%A
                    taskkill /PID %%A /T /F >nul 2>&1
                )

                echo.
                echo ===== PORT STATUS AFTER CLEANUP =====

                netstat -ano | findstr :3003

                echo.
                echo ===== PORT FORWARD LOG =====

                if exist k8s-port-forward.log (
                    type k8s-port-forward.log
                )
            '''
        }


        success {

            echo '========================================'
            echo 'AI-PERF-RCA PIPELINE SUCCESS'
            echo '========================================'
        }


        failure {

            echo '========================================'
            echo 'AI-PERF-RCA PIPELINE FAILED'
            echo '========================================'
        }
    }
}