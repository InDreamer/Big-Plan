为了将PL/SQL块添加到现有的Camel job中，你需要修改`dbarchive.properties`文件来包含新的PL/SQL语句，并更新Camel的配置以执行这些语句。

### 修改dbarchive.properties

添加新的PL/SQL块到 `dbarchive.properties` 文件：

```properties
# for MLS DB Archive
dbarchive.job.main1=delete from MESSAGE_JOURNAL_PROPERTY p where exists (select 1 from MESSAGE_JOURNAL j where j.CREATE_TIMESTAMP < ADD_MONTHS(trunc(sysdate) , -3 ) and j.id = p.message_id )
dbarchive.job.main2=delete from MESSAGE_JOURNAL where CREATE_TIMESTAMP < ADD_MONTHS(trunc(sysdate) , -3 )

dbarchive.job.cdu1=delete from MESSAGE_JOURNAL_PROPERTY p where exists (select 1 from MESSAGE_JOURNAL j where j.SOURCE_SYS_ID = 'MUREX_CDU' and j.CREATE_TIMESTAMP < ADD_MONTHS(trunc(sysdate) , -1 ) and j.id = p.message_id )
dbarchive.job.cdu2=delete from MESSAGE_JOURNAL where SOURCE_SYS_ID = 'MUREX_CDU' and CREATE_TIMESTAMP < ADD_MONTHS(trunc(sysdate) , -1 )
dbarchive.job.cdu3=delete from T_CDU_TRADES where create_timestamp < trunc(sysdate)-7 and STATUS = 'processed'
dbarchive.job.cdu4=delete from T_CDU_TI_VALUES where create_timestamp < trunc(sysdate)-7
dbarchive.job.shrink1=alter table MESSAGE_JOURNAL modify lob (CONTENT) (shrink space)
dbarchive.job.shrink2=alter table T_CDU_TRADES modify lob (CONTENT) (shrink space)

dbarchive.job.compress_partitions=BEGIN
FOR rec IN (
    SELECT PARTITION_NAME
    FROM (
        SELECT PARTITION_NAME,
               ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn
        FROM user_tab_partitions WHERE TABLE_NAME = 'MESSAGE_JOURNAL'
    )
    WHERE rn IN (2,3,4)
)
LOOP
    EXECUTE IMMEDIATE 'ALTER TABLE MESSAGE_JOURNAL MOVE PARTITION '||rec.PARTITION_NAME||' COMPRESS UPDATE indexes ONLINE';
END LOOP;
END;
```

### 修改Camel XML配置

确保Camel可以执行PL/SQL块。你可以在Camel XML配置中添加新的 `dbarchive.job.compress_partitions`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:context="http://www.springframework.org/schema/context"
       xsi:schemaLocation="http://www.springframework.org/schema/beans http://www.springframework.org/schema/beans/spring-beans-4.2.xsd
                           http://www.springframework.org/schema/context http://www.springframework.org/schema/context/spring-context-4.2.xsd
                           http://camel.apache.org/schema/spring http://camel.apache.org/schema/spring/camel-spring.xsd">
    <import resource="classpath:common/initDBDataSource.xml"/>
    <bean id="camelStopProcessor" class="com.scb.mxg.mls.utilities.dbarchive.processor.CamelStopProcessor"/>
    <camelContext xmlns="http://camel.apache.org/schema/spring">
        <propertyPlaceholder id="properties" location="classpath:application.properties,classpath:properties/dbarchive.properties" encoding="utf-8"/>
        <!--DB Archive-->
        <route autoStartup="true">
            <from uri="timer://DBArchive?repeatCount=1"/>
            <log message="DB Archive Started...${date:now:yyyy-MM-dd HH:mm:ss.SSS}"/>
            <setBody>
                <simple resultType="java.lang.String">{{dbarchive.jobs}}</simple>
            </setBody>
            <split>
                <tokenize token=","/>
                <setHeader headerName="job">
                    <simple>${body}</simple>
                </setHeader>
                <log message="${header.job} job started...${date:now:yyyy-MM-dd HH:mm:ss.SSS}"/>
                <log message="${properties:dbarchive.job.${header.job}}"/>
                <choice>
                    <when>
                        <simple>${header.job} == 'compress_partitions'</simple>
                        <to uri="plsql:{{dbarchive.job.${header.job}}}?dataSource=mlsDbDataSource"/>
                    </when>
                    <otherwise>
                        <recipientList>
                            <simple>sql:${properties:dbarchive.job.${header.job}}?dataSource=mlsDbDataSource</simple>
                        </recipientList>
                    </otherwise>
                </choice>
                <log message="updated count: ${header.CamelSqlUpdateCount}"/>
                <log message="${header.job} job ended...${date:now:yyyy-MM-dd HH:mm:ss.SSS}"/>
            </split>
            <log message="DB Archive Ended...${date:now:yyyy-MM-dd HH:mm:ss.SSS}"/>
            <process ref="camelStopProcessor"/>
        </route>
    </camelContext>
</beans>
```

### 关键点

1. **PL/SQL语句**：确保PL/SQL语句在 `dbarchive.properties` 中是单行的。如果太长，可以使用转义符 `\` 换行。
2. **Camel配置**：通过 `choice` 元素来区分是否要执行PL/SQL块。如果是 `compress_partitions`，则使用 `plsql` 组件，否则使用 `sql` 组件。
3. **数据源**：确保 `mlsDbDataSource` 在 `initDBDataSource.xml` 中正确配置。
通过这些修改，你的Camel job可以读取并执行新的PL/SQL块，完
成对最新第二、第三和第四个分区的压缩任务。

你的 Camel 作业主要是执行存储在 properties 文件中的 SQL 语句。虽然 Camel 可以执行 PL/SQL 块，但为了保持一致性和简单性，我们可以将你的 PL/SQL 块转换为等效的 SQL 语句。这样，我们就可以将这些语句添加到你的 dbarchive.properties 文件中。

以下是将 PL/SQL 块转换为一系列 SQL 语句的方法：

1. 首先，我们需要一个查询来获取第二、第三和第四个最新的分区：

```sql
SELECT PARTITION_NAME
FROM (
    SELECT PARTITION_NAME,
           ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn
    FROM user_tab_partitions 
    WHERE TABLE_NAME = 'MESSAGE_JOURNAL'
)
WHERE rn IN (2,3,4)
```

2. 然后，我们可以为每个分区创建单独的 ALTER TABLE 语句：

```sql
ALTER TABLE MESSAGE_JOURNAL MOVE PARTITION (
    SELECT PARTITION_NAME
    FROM (
        SELECT PARTITION_NAME,
               ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn
        FROM user_tab_partitions 
        WHERE TABLE_NAME = 'MESSAGE_JOURNAL'
    )
    WHERE rn = 2
) COMPRESS UPDATE indexes ONLINE;

ALTER TABLE MESSAGE_JOURNAL MOVE PARTITION (
    SELECT PARTITION_NAME
    FROM (
        SELECT PARTITION_NAME,
               ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn
        FROM user_tab_partitions 
        WHERE TABLE_NAME = 'MESSAGE_JOURNAL'
    )
    WHERE rn = 3
) COMPRESS UPDATE indexes ONLINE;

ALTER TABLE MESSAGE_JOURNAL MOVE PARTITION (
    SELECT PARTITION_NAME
    FROM (
        SELECT PARTITION_NAME,
               ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn
        FROM user_tab_partitions 
        WHERE TABLE_NAME = 'MESSAGE_JOURNAL'
    )
    WHERE rn = 4
) COMPRESS UPDATE indexes ONLINE;
```

现在，你可以将这些 SQL 语句添加到你的 dbarchive.properties 文件中，如下所示：

```properties
dbarchive.job.compress1=ALTER TABLE MESSAGE_JOURNAL MOVE PARTITION (SELECT PARTITION_NAME FROM (SELECT PARTITION_NAME, ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn FROM user_tab_partitions WHERE TABLE_NAME = 'MESSAGE_JOURNAL') WHERE rn = 2) COMPRESS UPDATE indexes ONLINE
dbarchive.job.compress2=ALTER TABLE MESSAGE_JOURNAL MOVE PARTITION (SELECT PARTITION_NAME FROM (SELECT PARTITION_NAME, ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn FROM user_tab_partitions WHERE TABLE_NAME = 'MESSAGE_JOURNAL') WHERE rn = 3) COMPRESS UPDATE indexes ONLINE
dbarchive.job.compress3=ALTER TABLE MESSAGE_JOURNAL MOVE PARTITION (SELECT PARTITION_NAME FROM (SELECT PARTITION_NAME, ROW_NUMBER() OVER (ORDER BY PARTITION_POSITION DESC) AS rn FROM user_tab_partitions WHERE TABLE_NAME = 'MESSAGE_JOURNAL') WHERE rn = 4) COMPRESS UPDATE indexes ONLINE
```

最后，更新你的 application.properties 文件，将这些新的作业添加到 dbarchive.jobs 列表中：

```properties
dbarchive.jobs=main1,main2,cdu1,cdu2,cdu3,cdu4,shrink1,shrink2,compress1,compress2,compress3
```

这种方法将允许你在现有的 Camel 作业中执行这些新的压缩操作，而无需更改 Camel 路由或引入 PL/SQL 块。每个压缩操作都将作为单独的作业运行，这也使得监控和错误处理变得更加容易。

请注意，这些 ALTER TABLE MOVE PARTITION 操作可能会消耗大量资源，特别是在大型表上。确保在非高峰时间运行这些操作，并密切监控其性能影响。