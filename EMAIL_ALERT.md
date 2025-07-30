# Email Alert Configuration for Airflow 3.0.2

## Overview
This document provides comprehensive guidance for setting up email notifications in Apache Airflow 3.0.2, including DAG-level alerts, task failure notifications, and custom email templates.


## Email Body Template (email_body_template.html)

```html
<html>
  <body>
    <p>DAG: {{ ti.dag_id }}</p>
    <p>Task: {{ ti.task_id }}</p>
    <p>Status: {{ ti.state }}</p>
    <p>Try: {{ ti.try_number }} / {{ ti.max_tries + 1 }}</p>
    <p>Exception: {{ exception }}</p>
  </body>
</html>

```
## Email Subject Template (email_subject_template.txt)

```txt
[Airflow] {{ ti.dag_id }}.{{ ti.task_id }} {{ ti.state }} - {{ ts }}
```



## DAG Example (alert failure)

```python

import pendulum
import logging
from airflow import DAG
from airflow.hooks.base import BaseHook
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.smtp.notifications.smtp import SmtpNotifier

logging.getLogger("smtplib").setLevel(logging.DEBUG)
logging.getLogger("airflow.utils.email").setLevel(logging.DEBUG)


default_args = {
    "owner": "airflow",
    "email": ["abc@gmail.com"],
    "email_on_failure": True,
    # email_on_retry: ตามความต้องการ
}

def fail_task():
    raise ValueError("Intentional failure to trigger email")

with DAG(
    dag_id="scb_ap1234_notify_test_v4",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    schedule="@once",
    catchup=False,
     default_args=default_args,
     tags=["scb_ap1234", "v4", "notify"],
) as dag:
    t = PythonOperator(
        task_id="fail_and_notify",
        python_callable=fail_task,
    )


```

## DAG Example (smtp direct)

```python

from airflow import DAG
from airflow.operators.python import PythonOperator
import pendulum
from airflow.utils.email import send_email
import logging

logging.getLogger("smtplib").setLevel(logging.DEBUG)
logging.getLogger("airflow.utils.email").setLevel(logging.DEBUG)

def send_test_email():
    send_email(
        to=["abc@gmail.com"],
        subject="✅ Direct SMTP Email from Airflow",
        html_content="<b>Sent directly using airflow.utils.email.send_email()</b>"
    )

with DAG(
    dag_id="scb_ap1234_notify_test_direct_smtp_email",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    schedule="@once",
    tags=["scb_ap1234", "v2", "builtin_alerts"],
    catchup=False,
) as dag:
    t = PythonOperator(
        task_id="send_email_task",
        python_callable=send_test_email,
    )

```



