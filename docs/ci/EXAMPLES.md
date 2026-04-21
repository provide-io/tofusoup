# Practical Examples

Real-world usage examples for `soup stir` CI/CD features across different platforms and scenarios.

## Table of Contents

- [GitHub Actions](#github-actions)
- [GitLab CI](#gitlab-ci)
- [Jenkins](#jenkins)
- [CircleCI](#circleci)
- [Local Development](#local-development)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

---

## GitHub Actions

### Basic Workflow

```yaml
name: Test Terraform Provider

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install TofuSoup
        run: |
          uv tool install tofusoup

      - name: Run provider tests
        run: |
          soup stir tests/
```

### With JUnit XML and Test Reporting

```yaml
name: Test Provider with Reports

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          uv tool install tofusoup

      - name: Run tests with JUnit output
        run: |
          soup stir \
            --junit-xml=test-results/results.xml \
            --junit-suite-name="Provider Conformance Tests" \
            --timeout=1800 \
            --test-timeout=300 \
            tests/

      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: test-results/results.xml
          check_name: 'Terraform Provider Tests'

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: test-results/
```

### With GitHub Annotations

```yaml
name: Provider Tests with Annotations

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install TofuSoup
        run: uv tool install tofusoup

      - name: Run tests with GitHub format
        run: |
          soup stir \
            --format=github \
            --timeout=1200 \
            tests/
```

### Matrix Testing Across Terraform Versions

```yaml
name: Multi-Version Provider Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        terraform_version: ['1.5.0', '1.6.0', '1.7.0']
      fail-fast: false

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Terraform ${{ matrix.terraform_version }}
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ matrix.terraform_version }}

      - name: Install TofuSoup
        run: uv tool install tofusoup

      - name: Run tests
        run: |
          soup stir \
            --junit-xml=results-${{ matrix.terraform_version }}.xml \
            --junit-suite-name="Tests (Terraform ${{ matrix.terraform_version }})" \
            --timeout=1800 \
            tests/

      - name: Upload results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: results-${{ matrix.terraform_version }}
          path: results-*.xml
```

### With JSON Output and Slack Notification

```yaml
name: Provider Tests with Notifications

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install TofuSoup
        run: uv tool install tofusoup

      - name: Run tests
        id: tests
        run: |
          soup stir --json tests/ > results.json
          echo "results=$(cat results.json | jq -c .)" >> $GITHUB_OUTPUT
        continue-on-error: true

      - name: Parse results
        id: parse
        run: |
          PASSED=$(jq '.summary.passed' results.json)
          FAILED=$(jq '.summary.failed' results.json)
          TOTAL=$(jq '.summary.total' results.json)
          echo "passed=$PASSED" >> $GITHUB_OUTPUT
          echo "failed=$FAILED" >> $GITHUB_OUTPUT
          echo "total=$TOTAL" >> $GITHUB_OUTPUT

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Provider Tests: ${{ steps.parse.outputs.passed }}/${{ steps.parse.outputs.total }} passed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Provider Test Results*\n✅ Passed: ${{ steps.parse.outputs.passed }}\n❌ Failed: ${{ steps.parse.outputs.failed }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

      - name: Fail if tests failed
        if: steps.parse.outputs.failed != '0'
        run: exit 1
```

---

## GitLab CI

### Basic Pipeline

```yaml
# .gitlab-ci.yml

stages:
  - test

test:terraform:
  stage: test
  image: python:3.11
  timeout: 30m
  script:
    - uv tool install tofusoup
    - soup stir tests/
```

### With JUnit and Artifacts

```yaml
# .gitlab-ci.yml

stages:
  - test

test:provider:
  stage: test
  image: python:3.11
  timeout: 30m

  script:
    - uv tool install tofusoup
    - |
      soup stir \
        --junit-xml=results.xml \
        --summary-file=summary.json \
        --timeout=1800 \
        --test-timeout=300 \
        tests/

  artifacts:
    when: always
    reports:
      junit: results.xml
    paths:
      - results.xml
      - summary.json
    expire_in: 30 days
```

### With Coverage and Caching

```yaml
# .gitlab-ci.yml

variables:
  UV_CACHE_DIR: "$CI_PROJECT_DIR/.cache/uv"

cache:
  paths:
    - .cache/uv
    - .terraform.d/plugin-cache

stages:
  - test

before_script:
  - uv tool install tofusoup

test:comprehensive:
  stage: test
  image: python:3.11
  timeout: 45m

  script:
    - |
      soup stir \
        --junit-xml=results.xml \
        --json > results.json \
        --summary-file=summary.md \
        --summary-format=markdown \
        --show-phase-timing \
        --timeout=2700 \
        tests/

  after_script:
    - cat summary.md

  artifacts:
    when: always
    reports:
      junit: results.xml
    paths:
      - results.xml
      - results.json
      - summary.md
```

### Parallel Jobs

```yaml
# .gitlab-ci.yml

stages:
  - test

.test_template: &test_definition
  stage: test
  image: python:3.11
  timeout: 20m
  script:
    - uv tool install tofusoup
    - soup stir --junit-xml=results-$TEST_SUITE.xml tests/$TEST_SUITE/
  artifacts:
    when: always
    reports:
      junit: results-$TEST_SUITE.xml

test:auth:
  <<: *test_definition
  variables:
    TEST_SUITE: "auth"

test:network:
  <<: *test_definition
  variables:
    TEST_SUITE: "network"

test:storage:
  <<: *test_definition
  variables:
    TEST_SUITE: "storage"
```

---

## Jenkins

### Declarative Pipeline

```groovy
// Jenkinsfile

pipeline {
    agent any

    parameters {
        string(name: 'TEST_TIMEOUT', defaultValue: '300', description: 'Per-test timeout in seconds')
        choice(name: 'PARALLELISM', choices: ['auto', '1', '2', '4'], description: 'Test parallelism')
    }

    options {
        timeout(time: 45, unit: 'MINUTES')
        timestamps()
    }

    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    uv tool install tofusoup
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . venv/bin/activate
                    soup stir \
                        --junit-xml=results.xml \
                        --summary-file=summary.json \
                        --timeout=2400 \
                        --test-timeout=${TEST_TIMEOUT} \
                        --jobs=${PARALLELISM} \
                        tests/
                '''
            }
        }
    }

    post {
        always {
            junit 'results.xml'

            archiveArtifacts artifacts: 'summary.json', allowEmptyArchive: true

            script {
                def summary = readJSON file: 'summary.json'
                echo "Tests: ${summary.summary.total}, Passed: ${summary.summary.passed}, Failed: ${summary.summary.failed}"
            }
        }

        failure {
            emailext (
                subject: "Provider Tests Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """
                    Test Results:
                    - Total: ${summary.summary.total}
                    - Passed: ${summary.summary.passed}
                    - Failed: ${summary.summary.failed}

                    Build URL: ${env.BUILD_URL}
                """,
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

### Scripted Pipeline with Parallel Stages

```groovy
// Jenkinsfile

node {
    stage('Checkout') {
        checkout scm
    }

    stage('Setup') {
        sh '''
            python3 -m venv venv
            . venv/bin/activate
            uv tool install tofusoup
        '''
    }

    stage('Test') {
        parallel(
            'Auth Tests': {
                sh '''
                    . venv/bin/activate
                    soup stir --junit-xml=results-auth.xml tests/auth/
                '''
            },
            'Network Tests': {
                sh '''
                    . venv/bin/activate
                    soup stir --junit-xml=results-network.xml tests/network/
                '''
            },
            'Storage Tests': {
                sh '''
                    . venv/bin/activate
                    soup stir --junit-xml=results-storage.xml tests/storage/
                '''
            }
        )
    }

    stage('Report') {
        junit 'results-*.xml'
        archiveArtifacts 'results-*.xml'
    }
}
```

---

## CircleCI

### Basic Configuration

```yaml
# .circleci/config.yml

version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  test:
    docker:
      - image: cimg/python:3.11

    steps:
      - checkout

      - run:
          name: Install uv
          command: |
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.local/bin:$PATH"
      - run:
          name: Install tofusoup
          command: uv tool install tofusoup

      - run:
          name: Run provider tests
          command: |
            soup stir \
              --junit-xml=test-results/results.xml \
              --timeout=1800 \
              tests/
          no_output_timeout: 30m

      - store_test_results:
          path: test-results

      - store_artifacts:
          path: test-results

workflows:
  test-workflow:
    jobs:
      - test
```

### With Multiple Test Suites

```yaml
# .circleci/config.yml

version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  test:
    parameters:
      suite:
        type: string

    docker:
      - image: cimg/python:3.11

    steps:
      - checkout

      - run:
          name: Install uv
          command: |
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.local/bin:$PATH"
      - run:
          name: Install tofusoup
          command: uv tool install tofusoup

      - run:
          name: Run << parameters.suite >> tests
          command: |
            soup stir \
              --junit-xml=results-<< parameters.suite >>.xml \
              --json > results-<< parameters.suite >>.json \
              --timeout=900 \
              tests/<< parameters.suite >>/

      - store_test_results:
          path: results-<< parameters.suite >>.xml

      - store_artifacts:
          path: results-<< parameters.suite >>.json

workflows:
  test-all:
    jobs:
      - test:
          matrix:
            parameters:
              suite: ["auth", "network", "storage", "compute"]
```

---

## Local Development

### Quick Test Run

```bash
# Run all tests interactively
soup stir tests/

# Run with timestamps for debugging
soup stir --timestamps tests/

# Serial execution for debugging
soup stir -j 1 tests/
```

### Debugging Failed Tests

```bash
# Run serially with phase timing
soup stir \
  -j 1 \
  --show-phase-timing \
  --stream-logs \
  tests/

# Stop at first failure
soup stir --fail-fast tests/

# Save detailed logs
soup stir \
  --aggregate-logs=debug.log \
  --logs-dir=./test-logs \
  tests/
```

### Generate Reports for Review

```bash
# Generate all report formats
soup stir \
  --json > results.json \
  --junit-xml=results.xml \
  --summary-file=summary.md \
  --summary-format=markdown \
  --show-phase-timing \
  tests/

# View JSON results with jq
jq '.tests[] | select(.status=="failed")' results.json

# View summary
cat summary.md
```

### Testing with Timeouts

```bash
# Test timeout behavior
soup stir \
  --test-timeout=30 \
  --timeout=120 \
  tests/

# Very short timeout to test handling
soup stir --test-timeout=5 tests/slow-test/
```

---

## Common Patterns

### Pattern 1: Full CI Test Run

Complete test run with all outputs for CI:

```bash
soup stir \
  --junit-xml=results.xml \
  --json > results.json \
  --summary-file=summary.md \
  --summary-format=markdown \
  --timeout=1800 \
  --test-timeout=300 \
  --show-phase-timing \
  tests/
```

**Use Case**: Production CI pipeline that needs:
- JUnit XML for test reporting
- JSON for custom processing
- Markdown summary for artifact review
- Timeouts to prevent hanging
- Phase timing for performance analysis

---

### Pattern 2: Fast Feedback Development

Quick test run during development:

```bash
soup stir \
  --fail-fast \
  -j 1 \
  --show-progress \
  tests/
```

**Use Case**: Local development when:
- Want to stop at first failure
- Running serially to avoid resource conflicts
- Need progress indicator

---

### Pattern 3: Comprehensive Debugging

Deep debugging of test failures:

```bash
soup stir \
  -j 1 \
  --stream-logs \
  --aggregate-logs=full-debug.log \
  --show-phase-timing \
  --timestamps \
  --timestamp-format=relative \
  tests/failed-test/
```

**Use Case**: Investigating test failures:
- Serial execution (deterministic order)
- All logs streamed to see real-time issues
- Aggregated logs for complete record
- Phase timing to find bottlenecks
- Relative timestamps to understand timing

---

### Pattern 4: Performance Testing

Analyze test performance:

```bash
soup stir \
  --json > perf-results.json \
  --show-phase-timing \
  --jobs=1 \
  tests/

# Analyze with jq
jq '.tests[] | {name: .name, duration: .duration_seconds, phases: .phase_timings}' perf-results.json
```

**Use Case**: Performance optimization:
- JSON for programmatic analysis
- Phase timing to identify slow phases
- Serial to eliminate parallelism effects

---

### Pattern 5: CI with Notifications

CI run with external notifications:

```bash
# Run tests
soup stir --json tests/ > results.json
EXIT_CODE=$?

# Parse results
PASSED=$(jq '.summary.passed' results.json)
FAILED=$(jq '.summary.failed' results.json)
TOTAL=$(jq '.summary.total' results.json)

# Send notification (Slack example)
if [ $EXIT_CODE -ne 0 ]; then
    curl -X POST $SLACK_WEBHOOK \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"Tests Failed: $FAILED/$TOTAL failed\"}"
fi

exit $EXIT_CODE
```

---

### Pattern 6: Multi-Environment Matrix

Test across multiple Terraform/Tofu versions:

```bash
#!/bin/bash

VERSIONS=("1.5.7" "1.6.0" "1.7.0")

for VERSION in "${VERSIONS[@]}"; do
    echo "Testing with Terraform $VERSION"

    # Switch Terraform version
    tfenv use $VERSION

    # Run tests
    soup stir \
      --junit-xml=results-${VERSION}.xml \
      --junit-suite-name="Tests (Terraform ${VERSION})" \
      --timeout=1200 \
      tests/

    if [ $? -ne 0 ]; then
        echo "Tests failed with Terraform $VERSION"
        exit 1
    fi
done

echo "All versions passed!"
```

---

## Troubleshooting

### Issue: Tests Timeout in CI

**Symptoms**:
- Tests exceed global timeout
- Exit code 124

**Solutions**:

```bash
# Increase timeouts
soup stir --timeout=3600 --test-timeout=600 tests/

# Run fewer tests in parallel (reduce resource contention)
soup stir --jobs=2 --timeout=1800 tests/

# Identify slow tests
soup stir --json tests/ | jq '.tests | sort_by(.duration_seconds) | reverse | .[0:5]'
```

---

### Issue: CI Logs are Cluttered

**Symptoms**:
- Too much output in CI logs
- Hard to find relevant information

**Solutions**:

```bash
# Use quiet mode
soup stir --format=quiet tests/

# Or plain mode without refresh
soup stir --format=plain --no-refresh tests/

# Or only show failures
soup stir --format=plain tests/ 2>&1 | grep -E '(FAIL|ERROR|❌)'
```

---

### Issue: Can't Parse Test Results

**Symptoms**:
- Need to process results programmatically
- Current output not machine-readable

**Solutions**:

```bash
# Use JSON output
soup stir --json tests/ > results.json

# Use JUnit XML
soup stir --junit-xml=results.xml tests/

# Both
soup stir --json --junit-xml=results.xml tests/ > results.json
```

---

### Issue: Parallel Tests Fail, Serial Passes

**Symptoms**:
- Tests pass with `-j 1`
- Tests fail with parallel execution

**Root Causes**:
- Resource conflicts (ports, files, etc.)
- Rate limiting
- Race conditions

**Solutions**:

```bash
# Reduce parallelism
soup stir --jobs=2 tests/

# Run serially in CI (if needed)
soup stir -j 1 tests/

# Isolate problem tests
soup stir -j 1 tests/problematic-test/
soup stir --jobs=4 tests/ --exclude tests/problematic-test/
```

---

### Issue: Need to Debug Test Failures

**Symptoms**:
- Test fails but error unclear
- Need more information

**Solutions**:

```bash
# Stream all logs
soup stir --stream-logs tests/failing-test/

# Aggregate logs to file
soup stir --aggregate-logs=debug.log tests/failing-test/

# Show phase timing to find where it fails
soup stir --show-phase-timing tests/failing-test/

# Run with full Terraform logs
TF_LOG=DEBUG soup stir tests/failing-test/
```

---

### Issue: GitHub Actions Not Showing Test Results

**Symptoms**:
- Tests run but no test reporter integration

**Solution**:

```yaml
- name: Run tests
  run: soup stir --junit-xml=results.xml tests/

- name: Publish test results
  uses: EnricoMi/publish-unit-test-result-action@v2
  if: always()
  with:
    files: results.xml
```

---

### Issue: Want to Track Test Performance Over Time

**Solution**:

```bash
# Generate JSON with timing data
soup stir --json --show-phase-timing tests/ > results-$(date +%Y%m%d).json

# Store in artifact storage
# In CI, upload to S3/GCS/etc.

# Analyze trends
jq '.tests[] | {name: .name, duration: .duration_seconds}' results-*.json
```

---

## Additional Resources

- [SPEC.md](./SPEC.md) - Complete specifications
- [API_REFERENCE.md](./API_REFERENCE.md) - All flags and options
- [OUTPUT_FORMATS.md](./OUTPUT_FORMATS.md) - Output format details

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-02
**Status**: Practical Examples Guide
