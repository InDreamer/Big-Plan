import org.apache.camel.Exchange;
import org.apache.camel.Message;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.powermock.api.mockito.PowerMockito;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.powermock.modules.junit4.PowerMockRunner;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

import static org.mockito.Mockito.*;

@RunWith(PowerMockRunner.class)
@PrepareForTest({File.class, Files.class})
public class UVTCompareProcessorTest {

    @Mock
    private Exchange exchange;

    @Mock
    private Message message;

    private UVTCompareProcessor processor;

    @Before
    public void setUp() {
        processor = new UVTCompareProcessor();
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

        // Mock File and Files static methods
        File mockFile = PowerMockito.mock(File.class);
        PowerMockito.whenNew(File.class).withAnyArguments().thenReturn(mockFile);
        PowerMockito.mockStatic(Files.class);
        PowerMockito.when(Files.toString(any(File.class), any())).thenReturn(expectedContent);

        // Execute the method
        processor.process(exchange);

        // Verify the result
        verify(message).setBody(argThat(arg -> arg.toString().contains("Difference found")));
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

        // Mock File and Files static methods
        File mockFile = PowerMockito.mock(File.class);
        PowerMockito.whenNew(File.class).withAnyArguments().thenReturn(mockFile);
        PowerMockito.mockStatic(Files.class);
        PowerMockito.when(Files.toString(any(File.class), any())).thenReturn(content);

        // Execute the method
        processor.process(exchange);

        // Verify the result
        verify(message).setBody("Those 2 files are exactly same");
    }
}
<dependency>
    <groupId>org.powermock</groupId>
    <artifactId>powermock-module-junit4</artifactId>
    <version>2.0.9</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.powermock</groupId>
    <artifactId>powermock-api-mockito2</artifactId>
    <version>2.0.9</version>
    <scope>test</scope>
</dependency>
