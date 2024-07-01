您的问题很详细，让我们逐步分析并提供建议：

1. 关于您当前使用的语句：

```sql
ALTER TABLE message_journal MOVE PARTITION partition_name COMPRESS UPDATE INDEXES ONLINE
```

这个语句是很好的，因为它：
- 压缩数据（COMPRESS）
- 更新索引（UPDATE INDEXES）
- 保持在线（ONLINE），减少停机时间

这是一个不错的方法，但可以根据您的具体需求进行优化。

2. 按月份选择分区执行：

您可以使用动态SQL来实现这一点。以下是一个示例 PL/SQL 过程：

```sql
CREATE OR REPLACE PROCEDURE optimize_partitions AS
  v_sql VARCHAR2(1000);
  v_partition_name VARCHAR2(100);
BEGIN
  -- 获取3个月前的日期
  FOR r IN (
    SELECT partition_name
    FROM user_tab_partitions
    WHERE table_name = 'MESSAGE_JOURNAL'
    AND to_date(substr(partition_name, instr(partition_name, '_', -1) + 1), 'YYYYMM') <= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -3)
  ) LOOP
    v_partition_name := r.partition_name;
    v_sql := 'ALTER TABLE message_journal MOVE PARTITION ' || v_partition_name || 
             ' COMPRESS UPDATE INDEXES ONLINE';
    EXECUTE IMMEDIATE v_sql;
    
    DBMS_STATS.GATHER_TABLE_STATS(
      ownname => USER,
      tabname => 'MESSAGE_JOURNAL',
      partname => v_partition_name,
      estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
      method_opt => 'FOR ALL COLUMNS SIZE AUTO',
      degree => 4,
      cascade => TRUE
    );
  END LOOP;
END;
/
```

这个过程会：
- 找到3个月前的所有分区
- 对每个分区执行MOVE PARTITION操作
- 收集每个处理过的分区的统计信息

3. 优化建议：

a. 自动化：
   设置一个每周运行的作业来执行这个过程。

b. 并行执行：
   如果您的系统资源允许，可以添加PARALLEL子句来加速操作：
   ```sql
   ' COMPRESS UPDATE INDEXES ONLINE PARALLEL 4'
   ```

c. 错误处理：
   添加错误处理逻辑，以便在某个分区出现问题时不会影响整个过程。

d. 日志记录：
   添加日志记录，跟踪每次优化的结果。

e. 空间监控：
   在优化前后检查空间使用情况，以评估优化效果。

4. 数据保留和删除：

对于只保存三个月数据的需求：

a. 使用基于范围的分区：
   确保您的分区策略是基于日期范围的。

b. 自动删除旧分区：
   使用分区交换（EXCHANGE PARTITION）和删除来管理旧数据：

```sql
CREATE OR REPLACE PROCEDURE manage_old_partitions AS
  v_partition_name VARCHAR2(100);
  v_temp_table_name VARCHAR2(100);
BEGIN
  FOR r IN (
    SELECT partition_name
    FROM user_tab_partitions
    WHERE table_name = 'MESSAGE_JOURNAL'
    AND to_date(substr(partition_name, instr(partition_name, '_', -1) + 1), 'YYYYMM') < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -3)
  ) LOOP
    v_partition_name := r.partition_name;
    v_temp_table_name := 'TEMP_' || v_partition_name;
    
    -- 创建临时表
    EXECUTE IMMEDIATE 'CREATE TABLE ' || v_temp_table_name || ' AS SELECT * FROM message_journal WHERE 1=0';
    
    -- 交换分区
    EXECUTE IMMEDIATE 'ALTER TABLE message_journal EXCHANGE PARTITION ' || v_partition_name || 
                      ' WITH TABLE ' || v_temp_table_name || ' INCLUDING INDEXES';
    
    -- 删除临时表（实际上是删除旧数据）
    EXECUTE IMMEDIATE 'DROP TABLE ' || v_temp_table_name || ' PURGE';
    
    -- 可选：删除空分区
    -- EXECUTE IMMEDIATE 'ALTER TABLE message_journal DROP PARTITION ' || v_partition_name;
  END LOOP;
END;
/
```

这个过程会：
- 找到3个月前的所有分区
- 将每个旧分区与一个空临时表交换
- 删除临时表（实际上删除了旧数据）
- 可选地删除空分区

5. 综合建议：

- 每周运行优化程序，处理3-4个月内的分区。
- 每月运行一次删除旧数据的程序。
- 监控空间使用情况和查询性能，根据需要调整优化频率。
- 在非高峰时段执行这些维护任务。
- 定期审查这个策略，确保它仍然满足您的需求。

通过这种方法，您可以自动化管理分区、优化空间使用，并保持数据在所需的时间范围内。请记得在生产环境中实施前，在测试环境中充分测试这些程序。

你的 `ALTER TABLE ... MOVE PARTITION ... COMPRESS ...` 语句是有效的，用于对特定分区进行压缩并回收空间。不过，这个语句一次只能针对一个分区。如果你每个月都会生成一个新分区，并且每周进行一次空间优化，可以编写一个脚本自动选择并优化需要的分区。

以下是一个示例脚本，用于按照月份选择并压缩需要优化的分区：

```sql
DECLARE
    v_partition_name VARCHAR2(50);
    v_table_name     VARCHAR2(50) := 'message_journal';
    v_owner          VARCHAR2(50) := 'your_schema';
    v_months_to_keep NUMBER       := 3;
BEGIN
    FOR rec IN (
        SELECT partition_name
        FROM dba_tab_partitions
        WHERE table_owner = v_owner
          AND table_name = v_table_name
          AND partition_position <= 
              (SELECT max(partition_position) - v_months_to_keep 
               FROM dba_tab_partitions
               WHERE table_owner = v_owner
                 AND table_name = v_table_name)
    ) LOOP
        v_partition_name := rec.partition_name;
        
        EXECUTE IMMEDIATE 'ALTER TABLE ' || v_owner || '.' || v_table_name || 
                          ' MOVE PARTITION ' || v_partition_name || 
                          ' COMPRESS UPDATE INDEXES ONLINE';
    END LOOP;
END;
/
```

这个脚本将自动查找并压缩超出保留期限（即三个月）的分区。你可以根据需要调整 `v_months_to_keep` 变量的值。

### 优化建议

1. **自动化任务**：可以使用 Oracle 的调度程序（DBMS_SCHEDULER）来每周自动运行上述脚本。
2. **删除过期分区**：确保在压缩之前已经删除过期的数据分区。可以使用以下命令：

```sql
ALTER TABLE message_journal DROP PARTITION partition_name;
```

你可以在压缩脚本之前先删除过期分区：

```sql
DECLARE
    v_partition_name VARCHAR2(50);
    v_table_name     VARCHAR2(50) := 'message_journal';
    v_owner          VARCHAR2(50) := 'your_schema';
    v_date_limit     DATE         := ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -3);
BEGIN
    FOR rec IN (
        SELECT partition_name
        FROM dba_tab_partitions
        WHERE table_owner = v_owner
          AND table_name = v_table_name
          AND to_date(partition_name, 'YYYYMM') < to_char(v_date_limit, 'YYYYMM')
    ) LOOP
        v_partition_name := rec.partition_name;
        
        EXECUTE IMMEDIATE 'ALTER TABLE ' || v_owner || '.' || v_table_name || 
                          ' DROP PARTITION ' || v_partition_name;
    END LOOP;
END;
/
```

然后运行压缩脚本：

```sql
DECLARE
    v_partition_name VARCHAR2(50);
    v_table_name     VARCHAR2(50) := 'message_journal';
    v_owner          VARCHAR2(50) := 'your_schema';
    v_months_to_keep NUMBER       := 3;
BEGIN
    FOR rec IN (
        SELECT partition_name
        FROM dba_tab_partitions
        WHERE table_owner = v_owner
          AND table_name = v_table_name
          AND partition_position <= 
              (SELECT max(partition_position) - v_months_to_keep 
               FROM dba_tab_partitions
               WHERE table_owner = v_owner
                 AND table_name = v_table_name)
    ) LOOP
        v_partition_name := rec.partition_name;
        
        EXECUTE IMMEDIATE 'ALTER TABLE ' || v_owner || '.' || v_table_name || 
                          ' MOVE PARTITION ' || v_partition_name || 
                          ' COMPRESS UPDATE INDEXES ONLINE';
    END LOOP;
END;
/
```

这样可以确保每次优化时，过期的数据已经删除，压缩操作也能顺利进行。
private static List<PartitionInfo> getPartitionsInfo(Connection conn) throws SQLException {
    List<PartitionInfo> partitions = new ArrayList<>();
    String sql = "SELECT partition_name, " +
                 "CASE " +
                 "  WHEN interval IS NOT NULL THEN " +
                 "    TO_DATE(TRIM(TRAILING ')' FROM TRIM(LEADING 'TIMESTAMP' FROM high_value))) " +
                 "  ELSE " +
                 "    TO_DATE(TRIM(BOTH '''' FROM TRIM(LEADING 'TO_DATE(' FROM TRIM(TRAILING ')' FROM high_value)))) " +
                 "END AS partition_date " +
                 "FROM user_tab_partitions " +
                 "WHERE table_name = 'MESSAGE_JOURNAL' " +
                 "ORDER BY partition_position";
    
    try (Statement stmt = conn.createStatement();
         ResultSet rs = stmt.executeQuery(sql)) {
        while (rs.next()) {
            String partitionName = rs.getString("partition_name");
            Date partitionDate = rs.getDate("partition_date");
            partitions.add(new PartitionInfo(partitionName, partitionDate));
        }
    }
    return partitions;
}

private static class PartitionInfo {
    String name;
    Date date;

    PartitionInfo(String name, Date date) {
        this.name = name;
        this.date = date;
    }
}


import java.sql.*;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

public class DatabaseOptimizer {

    private static final String DB_URL = "jdbc:oracle:thin:@your_database_url:1521/your_service_name";
    private static final String USER = "your_username";
    private static final String PASS = "your_password";

    public static void main(String[] args) {
        try (Connection conn = DriverManager.getConnection(DB_URL, USER, PASS)) {
            optimizePartitions(conn);
            manageOldPartitions(conn);
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }

    private static void optimizePartitions(Connection conn) throws SQLException {
        List<String> partitionsToOptimize = getPartitionsToOptimize(conn);
        for (String partitionName : partitionsToOptimize) {
            optimizePartition(conn, partitionName);
        }
    }

    private static List<String> getPartitionsToOptimize(Connection conn) throws SQLException {
        List<String> partitions = new ArrayList<>();
        LocalDate threeMonthsAgo = LocalDate.now().minusMonths(3);
        String sql = "SELECT partition_name FROM user_tab_partitions " +
                     "WHERE table_name = 'MESSAGE_JOURNAL' " +
                     "AND to_date(substr(partition_name, instr(partition_name, '_', -1) + 1), 'YYYYMM') >= ?";
        
        try (PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setDate(1, java.sql.Date.valueOf(threeMonthsAgo));
            try (ResultSet rs = pstmt.executeQuery()) {
                while (rs.next()) {
                    partitions.add(rs.getString("partition_name"));
                }
            }
        }
        return partitions;
    }

    private static void optimizePartition(Connection conn, String partitionName) throws SQLException {
        String sql = "ALTER TABLE message_journal MOVE PARTITION " + partitionName + 
                     " COMPRESS UPDATE INDEXES ONLINE";
        try (Statement stmt = conn.createStatement()) {
            stmt.execute(sql);
            System.out.println("Optimized partition: " + partitionName);
        }
        
        // Gather statistics
        String statsSql = "BEGIN " +
                          "DBMS_STATS.GATHER_TABLE_STATS(" +
                          "ownname => USER, " +
                          "tabname => 'MESSAGE_JOURNAL', " +
                          "partname => ?, " +
                          "estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE, " +
                          "method_opt => 'FOR ALL COLUMNS SIZE AUTO', " +
                          "degree => 4, " +
                          "cascade => TRUE" +
                          "); END;";
        try (CallableStatement cstmt = conn.prepareCall(statsSql)) {
            cstmt.setString(1, partitionName);
            cstmt.execute();
            System.out.println("Gathered statistics for partition: " + partitionName);
        }
    }

    private static void manageOldPartitions(Connection conn) throws SQLException {
        List<String> oldPartitions = getOldPartitions(conn);
        for (String partitionName : oldPartitions) {
            removeOldPartition(conn, partitionName);
        }
    }

    private static List<String> getOldPartitions(Connection conn) throws SQLException {
        List<String> partitions = new ArrayList<>();
        LocalDate threeMonthsAgo = LocalDate.now().minusMonths(3);
        String sql = "SELECT partition_name FROM user_tab_partitions " +
                     "WHERE table_name = 'MESSAGE_JOURNAL' " +
                     "AND to_date(substr(partition_name, instr(partition_name, '_', -1) + 1), 'YYYYMM') < ?";
        
        try (PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setDate(1, java.sql.Date.valueOf(threeMonthsAgo));
            try (ResultSet rs = pstmt.executeQuery()) {
                while (rs.next()) {
                    partitions.add(rs.getString("partition_name"));
                }
            }
        }
        return partitions;
    }

    private static void removeOldPartition(Connection conn, String partitionName) throws SQLException {
        String tempTableName = "TEMP_" + partitionName;
        
        // Create temporary table
        String createTempSql = "CREATE TABLE " + tempTableName + " AS SELECT * FROM message_journal WHERE 1=0";
        try (Statement stmt = conn.createStatement()) {
            stmt.execute(createTempSql);
            System.out.println("Created temporary table: " + tempTableName);
        }

        // Exchange partition
        String exchangeSql = "ALTER TABLE message_journal EXCHANGE PARTITION " + partitionName + 
                             " WITH TABLE " + tempTableName + " INCLUDING INDEXES";
        try (Statement stmt = conn.createStatement()) {
            stmt.execute(exchangeSql);
            System.out.println("Exchanged partition: " + partitionName);
        }

        // Drop temporary table (effectively removing old data)
        String dropTempSql = "DROP TABLE " + tempTableName + " PURGE";
        try (Statement stmt = conn.createStatement()) {
            stmt.execute(dropTempSql);
            System.out.println("Dropped temporary table (removed old data): " + tempTableName);
        }

        // Optionally, drop the empty partition
        // String dropPartitionSql = "ALTER TABLE message_journal DROP PARTITION " + partitionName;
        // try (Statement stmt = conn.createStatement()) {
        //     stmt.execute(dropPartitionSql);
        //     System.out.println("Dropped empty partition: " + partitionName);
        // }
    }
}


import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;

public class PartitionHousekeeping {
    private static final String DB_URL = "jdbc:oracle:thin:@your_db_host:1521:your_service_name";
    private static final String DB_USER = "your_username";
    private static final String DB_PASSWORD = "your_password";
    private static final String TABLE_NAME = "message_journal";
    private static final String SCHEMA_NAME = "your_schema";
    private static final int MONTHS_TO_KEEP = 3;

    public static void main(String[] args) {
        try (Connection conn = DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD)) {
            deleteOldPartitions(conn);
            compressPartitions(conn);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void deleteOldPartitions(Connection conn) throws Exception {
        String query = "SELECT partition_name FROM dba_tab_partitions " +
                       "WHERE table_owner = ? AND table_name = ? AND " +
                       "TO_DATE(partition_name, 'YYYYMM') < TO_CHAR(ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -?), 'YYYYMM')";
        
        try (PreparedStatement pstmt = conn.prepareStatement(query)) {
            pstmt.setString(1, SCHEMA_NAME.toUpperCase());
            pstmt.setString(2, TABLE_NAME.toUpperCase());
            pstmt.setInt(3, MONTHS_TO_KEEP);

            try (ResultSet rs = pstmt.executeQuery()) {
                while (rs.next()) {
                    String partitionName = rs.getString("partition_name");
                    String dropPartitionSql = "ALTER TABLE " + SCHEMA_NAME + "." + TABLE_NAME + " DROP PARTITION " + partitionName;
                    try (Statement stmt = conn.createStatement()) {
                        stmt.execute(dropPartitionSql);
                        System.out.println("Dropped partition: " + partitionName);
                    }
                }
            }
        }
    }

    private static void compressPartitions(Connection conn) throws Exception {
        String query = "SELECT partition_name FROM dba_tab_partitions " +
                       "WHERE table_owner = ? AND table_name = ? AND " +
                       "partition_position <= (SELECT MAX(partition_position) - ? " +
                       "FROM dba_tab_partitions WHERE table_owner = ? AND table_name = ?)";

        try (PreparedStatement pstmt = conn.prepareStatement(query)) {
            pstmt.setString(1, SCHEMA_NAME.toUpperCase());
            pstmt.setString(2, TABLE_NAME.toUpperCase());
            pstmt.setInt(3, MONTHS_TO_KEEP);
            pstmt.setString(4, SCHEMA_NAME.toUpperCase());
            pstmt.setString(5, TABLE_NAME.toUpperCase());

            try (ResultSet rs = pstmt.executeQuery()) {
                while (rs.next()) {
                    String partitionName = rs.getString("partition_name");
                    String compressPartitionSql = "ALTER TABLE " + SCHEMA_NAME + "." + TABLE_NAME + 
                                                  " MOVE PARTITION " + partitionName + 
                                                  " COMPRESS UPDATE INDEXES ONLINE";
                    try (Statement stmt = conn.createStatement()) {
                        stmt.execute(compressPartitionSql);
                        System.out.println("Compressed partition: " + partitionName);
                    }
                }
            }
        }
    }
}