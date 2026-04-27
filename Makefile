.PHONY: build test deploy clean

IMAGE_NAME ?= playwright-lambda
CONTAINER_NAME ?= playwright-lambda-test
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

deploy: build
	sam build --template infra/template.yaml
	sam deploy --guided --stack-name playwright-lambda

clean:
	@docker rm -f $(CONTAINER_NAME) 2>/dev/null || true
	@docker rmi $(IMAGE_NAME) 2>/dev/null || true
