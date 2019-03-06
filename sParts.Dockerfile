FROM sameerfarooq/sparts-test:latest

COPY ./phyo/processor/handler.py /project/src/tp_category_1.0/sawtooth_category/processor/handler.py
COPY ./phyo/category_cli.py /project/src/tp_category_1.0/sawtooth_category/category_cli.py
COPY ./phyo/category_batch.py /project/src/tp_category_1.0/sawtooth_category/category_batch.py

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/* && \
    cd /project/src/tp_category_1.0 && \
    python3 setup.py install \
