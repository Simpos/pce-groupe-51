.PHONY: all compile test deploy zip

# Commande par défaut si vous tapez juste "make"
all: compile test deploy

compile:
	pb_tool compile

test:
	python3 -m pytest tests -v

deploy: compile test
	pb_tool deploy -y

zip: compile test
	pb_tool zip

doc:
	pb_tool doc
