CREATE schema IF NOT EXISTS {{redshiftschema}} authorization {{redshiftusername}};

SET search_path TO {{redshiftschema}};

DROP TABLE if exists DEMO_SUPERSTORE_SALES_PROFITS CASCADE;
CREATE TABLE DEMO_SUPERSTORE_SALES_PROFITS
(
  ID       VARCHAR(50),
  Sales    NUMERIC(10,2),
  Profit   NUMERIC(10,2)
);


copy DEMO_SUPERSTORE_SALES_PROFITS
from 's3://{{s3bucketname}}/{{s3bucketpath}}'
credentials 'aws_iam_role=arn:aws:iam::{{awsaccountid}}:role/{{awsrole}}'
ignoreheader 1
TRIMBLANKS delimiter '|';

select count(*) from DEMO_SUPERSTORE_SALES_PROFITS;