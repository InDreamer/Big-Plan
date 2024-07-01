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