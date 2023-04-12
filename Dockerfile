# Copyright (c) 2016, 2023, Oracle and/or its affiliates.  All rights reserved.
# This software is licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl

FROM python:3-slim

LABEL author="KC Flynn" \
      email="kc.flynn@oracle.com"

WORKDIR /app

COPY *.py requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt && useradd scale && chown -R scale /app

USER scale

ENTRYPOINT ["python", "AutoScaleALL.py"]
