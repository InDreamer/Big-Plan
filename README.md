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

通过这些修改，你的Camel job可以读取并执行新的PL/SQL块，完成对最新第二、第三和第四个分区的压缩任务。