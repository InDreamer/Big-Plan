import org.apache.camel.Exchange;
import org.apache.camel.Message;
import org.apache.camel.impl.DefaultCamelContext;
import org.apache.camel.impl.DefaultExchange;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

import static org.junit.Assert.assertEquals;
import static org.mockito.Mockito.*;

public class YourClassNameIT {

    @Mock
    private Exchange exchange;

    @Mock
    private Message message;

    private YourClassName yourClass;

    @Before
    public void setUp() {
        MockitoAnnotations.initMocks(this);
        yourClass = new YourClassName();
        when(exchange.getIn()).thenReturn(message);
    }

    @Test
    public void testProcessWithDifferences() throws Exception {
        // Mock input data
        String module = "testModule";
        String fileName = "testFile.xml";
        String expectedContent = "<root><element>Expected</element></root>";
        String actualContent = "<root><element>Actual</element></root>";

        // Mock exchange headers and body
        when(message.getHeader("module", String.class)).thenReturn(module);
        when(message.getHeader("CamelFileName", String.class)).thenReturn(fileName);
        when(message.getBody(String.class)).thenReturn(actualContent);

        // Create a temporary file for the expected content
        File tempFile = createTempFileWithContent(expectedContent);
        
        // Mock the File creation
        try (MockedStatic<File> fileMock = mockStatic(File.class)) {
            fileMock.when(() -> new File("/appmls/coordinator/projects/utilities/uvt/expected/Expected_" + fileName))
                    .thenReturn(tempFile);

            // Execute the method
            yourClass.process(exchange);

            // Verify the result
            verify(message).setBody(argThat(arg -> arg.toString().contains("Difference found")));
        }
    }

    @Test
    public void testProcessWithoutDifferences() throws Exception {
        // Mock input data
        String module = "testModule";
        String fileName = "testFile.xml";
        String content = "<root><element>Same</element></root>";

        // Mock exchange headers and body
        when(message.getHeader("module", String.class)).thenReturn(module);
        when(message.getHeader("CamelFileName", String.class)).thenReturn(fileName);
        when(message.getBody(String.class)).thenReturn(content);

        // Create a temporary file for the expected content
        File tempFile = createTempFileWithContent(content);
        
        // Mock the File creation
        try (MockedStatic<File> fileMock = mockStatic(File.class)) {
            fileMock.when(() -> new File("/appmls/coordinator/projects/utilities/uvt/expected/Expected_" + fileName))
                    .thenReturn(tempFile);

            // Execute the method
            yourClass.process(exchange);

            // Verify the result
            verify(message).setBody("Those 2 files are exactly same");
        }
    }

    private File createTempFileWithContent(String content) throws IOException {
        File tempFile = File.createTempFile("expected", ".xml");
        tempFile.deleteOnExit();
        Files.write(tempFile.toPath(), content.getBytes(StandardCharsets.UTF_8));
        return tempFile;
    }
}