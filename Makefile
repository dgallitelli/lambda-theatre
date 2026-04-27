.PHONY: build build-lightpanda test test-lightpanda test-unit test-all test-all-lightpanda deploy clean

IMAGE_NAME ?= lambda-theatre
CONTAINER_NAME ?= lambda-theatre-test
PORT ?= 9000

build:
	docker build -t $(IMAGE_NAME) src/

test: build
	@docker rm -f $(CONTAINER_NAME) 2>/dev/null || true
	docker run -d --name $(CONTAINER_NAME) -p $(PORT):8080 $(IMAGE_NAME)
	@sleep 3
	@echo "--- Smoke test: page title ---"
	@curl -s -XPOST "http://localhost:$(PORT)/2015-03-31/functions/function/invocations" \
		-d '{"url": "https://example.com", "script": "result[\"title\"] = page.title()"}' | python3 -m json.tool
	@echo ""
	@echo "--- SPA test: TodoMVC React fill + click ---"
	@curl -s -XPOST "http://localhost:$(PORT)/2015-03-31/functions/function/invocations" \
		-d '{"url":"https://todomvc.com/examples/react/dist/","script":"page.wait_for_selector(\"input.new-todo\")\npage.fill(\"input.new-todo\",\"Test\")\npage.press(\"input.new-todo\",\"Enter\")\nresult[\"count\"]=page.locator(\"ul.todo-list li\").count()"}' | python3 -m json.tool
	@docker rm -f $(CONTAINER_NAME)

test-unit:
	pytest tests/test_invoke_cli.py -v

test-all: build
	pytest tests/ -v --timeout=120

deploy: build
	sam build --template infra/template.yaml
	sam deploy --guided --stack-name lambda-theatre

clean:
	@docker rm -f $(CONTAINER_NAME) 2>/dev/null || true
	@docker rmi $(IMAGE_NAME) 2>/dev/null || true

LP_IMAGE_NAME ?= lambda-theatre-lightpanda
LP_CONTAINER_NAME ?= lambda-theatre-lp-test

build-lightpanda:
	docker build -t $(LP_IMAGE_NAME) -f src/Dockerfile.lightpanda src/

test-lightpanda: build-lightpanda
	@docker rm -f $(LP_CONTAINER_NAME) 2>/dev/null || true
	docker run -d --name $(LP_CONTAINER_NAME) -p $(PORT):8080 $(LP_IMAGE_NAME)
	@sleep 8
	@echo "--- Smoke test: page title (Lightpanda) ---"
	@curl -s -XPOST "http://localhost:$(PORT)/2015-03-31/functions/function/invocations" \
		-d '{"url": "https://example.com", "script": "result[\"title\"] = page.title()"}' | python3 -m json.tool
	@echo ""
	@echo "--- SPA test: TodoMVC React fill + click (Lightpanda) ---"
	@curl -s -XPOST "http://localhost:$(PORT)/2015-03-31/functions/function/invocations" \
		-d '{"url":"https://todomvc.com/examples/react/dist/","script":"page.wait_for_selector(\"input.new-todo\")\npage.fill(\"input.new-todo\",\"Test\")\npage.press(\"input.new-todo\",\"Enter\")\nresult[\"count\"]=page.locator(\"ul.todo-list li\").count()"}' | python3 -m json.tool
	@docker rm -f $(LP_CONTAINER_NAME)

test-all-lightpanda: build-lightpanda
	pytest tests/ -v --timeout=120 -k lightpanda
