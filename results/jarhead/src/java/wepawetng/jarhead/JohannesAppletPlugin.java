package wepawetng.jarhead;

import java.net.*;
import java.util.Date;
import java.io.*;
import java.util.*;
import java.lang.*;
import java.sql.*;
import llweb.plugins.AppletPlugin;
import java.security.MessageDigest;
import java.math.BigInteger;
import org.apache.commons.logging.*;

public class JohannesAppletPlugin extends AppletPlugin {

    //constants
    private static final String analyzer= "/opt/bin/appletanalysis_run.sh";
    private static final String version_id = "1.0";
    private static final String plugin_name = "Jarhead";
    private static final String config_file = "/opt/etc/llweb-worker.conf";

    //class variables
    private static Log log = LogFactory.getLog(JohannesAppletPlugin.class);

    //config variables
    private static boolean have_config = false;
    private static String db_name = null;
    private static String db_user = null;
    private static String db_host = null;
    private static String db_pass = null;

    private static boolean apply_config(Properties props) {
        if (! have_config) {
            db_name = props.getProperty("db");
            db_user = props.getProperty("user");
            db_host = props.getProperty("host");
            db_pass = props.getProperty("passwd");

            return db_name != null && db_user != null && db_host != null && db_pass != null;
        } else {
            return true;
        }
    }

    private static void config() throws IOException {
        if (! have_config) {
            Properties props = new Properties();
            FileInputStream fi = new FileInputStream(new File(config_file));
            try {
                props.load(fi);
            } finally {
                fi.close();
            }
            have_config = apply_config(props);
            if (! have_config) {
                throw new IOException("Config values missing");
            }
        }
    }

    public JohannesAppletPlugin() throws IOException {
        config();
    }

    private String md5sum(InputStream is) {
        byte[] buffer = new byte[8192];
        int read = 0;
        String output = "";
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("MD5");
        } catch (Exception e) {
            log.error("Unable to get MD5" + e.toString());
            return output;
        }
        try {
            while( (read = is.read(buffer)) > 0) {
                digest.update(buffer, 0, read);
            }
            byte[] md5sum = digest.digest();
            BigInteger bigInt = new BigInteger(1, md5sum);
            output = bigInt.toString(16);
        }
        catch(IOException e) {
            log.error("Unable to process file for MD5 " + e.toString());
        }
        return output;
    }

    //<report>
    //<NAME_version>VERSION</NAME_version>
    //<id>HASH_OF_JAR</id>
    //<timestamp>TIMESTAMP OF ANALYSIS</timestamp>
    //<classification>(benign|suspicious|malicious)</classification>
    //<exploits>
    //<name>SHORT_NAME_OF_EXPLOIT</name>
    //<desc>DESC_OF_EXPLOIT (2 lines max)</desc>
    //<reference_id>CVE-XXXX-XX</reference_id>
    //<reference_url>http://cve.mitre.org/id=CVE_XXXX_XX</reference_url>
    //</exploits>
    //</report>

    private String generate_cve_description(String CVE) {
        String desc = "";
        if (CVE.matches("CVE-2009-3867")) {
            desc = "Stack-based buffer overflow in the HsbParser.getSoundBank function.\nRemote attackers can execute arbitrary code.";
        } else if (CVE.matches("CVE-2010-0842")) {
            desc = "MixerSequencer invalid array index remote code Execution vulnerability.\nRemote attackers can execute arbitrary code.";
        } else if (CVE.matches("CVE-2010-0094")) {
            desc = "Flaw within the deserialization of RMIConnectionImpl objects bypasses privilege checks.\nRemote attackers can execute arbitrary code.";
        } else if (CVE.matches("CVE-2008-5353")) {
            desc = "Improperly enforced context of ZoneInfo objects during deserialization bypasses privilege checks.\nRemote attackers can run untrusted applets and applications in a privileged context.";
        } else if (CVE.matches("CVE-2011-3544")) {
            desc = "Improper handling of Rhino JS errors.\nRemote attackers can run arbitrary Java code outside of the sandbox.";
        } else if (CVE.matches("CVE-2004-2626")) {
            desc = "GUI overlay vulnerability in the Java API in Siemens S55 cellular phones.\nAllows remote attackers to send unauthorized SMS.";
        } else if (CVE.matches("CVE-2010-0840")) {
            desc = "Flaw in ensuring proper privileged execution of methods (Trusted Method Chaining).\nRemote attackers can execute arbitrary code.";
        } else if (CVE.matches("CVE-2012-0507")) {
		desc = "Flaw in AtomicReferenceArray bypasses java sandbox.\nRemote attackers can execute arbitrary code.";
        } else {
            log.warn("Missing description for: " + CVE);
        }
        return desc;
    }

    private String generate_report_string(int stage, String[] result_fields, String sample, boolean failed) {
        String result = "";
        result += "<report>";
        result += "<appletanalysis_version>" + version_id + "</appletanalysis_version>";
        result += "<id>" + sample + "</id>";
        result += "<timestamp>" + new Date().toLocaleString() + "</timestamp>";
        if (! failed) {
	    if (stage == 2 && result_fields[0].matches("malicious")) {
		result += "<classification>suspicious</classification>";
	    } else {
		result += "<classification>" + result_fields[0] + "</classification>";
	    }
            result += "<exploits>";
	    if (stage == 1) {
                for (int i = 1; i < result_fields.length; i++) {
                    result += "<exploit>";
                    if (! result_fields[i].matches("EXECUTE")) {
                        result += "<desc>" + generate_cve_description(result_fields[i]) + "</desc>";
                        result += "<reference_id>" + result_fields[i] + "</reference_id>";
                        result += "<reference_url>http://cve.mitre.org/cgi-bin/cvename.cgi?name=" + result_fields[i] + "</reference_url>";
                    } else {
                        result += "<desc>Has potential to execute commands or download and run a program</desc>";
                        result += "<reference_id>None</reference_id>";
                        result += "<reference_url>None</reference_url>";
                    }
                    result += "</exploit>";
                }
	    }
            result += "</exploits>";
        } else {
            result += "<classification>" + "Error" + "</classification>";
        }
        result += "</report>";
        return result;
    }

    //| id                            | int(11)                         | NO   | PRI | NULL    | auto_increment |
    //| task_id               | int(11)                         | YES  | MUL | NULL    |                |
    //| plugin_name   | varchar(32)                     | YES  |     | NULL    |                |
    //| plugin_type           | enum('shellcode','postprocess') | YES  |     | NULL    |                |
    //| plugin_version   | varchar(16)                     | YES  |     | NULL    |                |
    //| result_raw            | mediumtext                      | YES  |     | NULL    |                |
    //| result_html           | mediumtext                      | YES  |     | NULL    |                |
    //| status                        | enum('pending','done','error')  | YES  |     | NULL    |                |
    //| subject_id            | text

    private void submit_result(int stage, String result, int taskId, boolean failed, String sample) {
        log.debug("Storing result for " + taskId);
        String[] fields = null;
	if (! failed) {
		fields = result.split(" ");
	}
        boolean submitted = false;
        Connection conn = null;

        try {
            Class.forName("com.mysql.jdbc.Driver").newInstance();
            log.debug("Connecting to: " + "jdbc:mysql://" + db_host + "/" + db_name + "?user=" + db_user + "&password=" + db_pass);

            conn = DriverManager.getConnection("jdbc:mysql://" + db_host + "/" + db_name + "?user=" + db_user + "&password=" + db_pass);

            PreparedStatement pstmt = conn.prepareStatement("INSERT INTO task_plugins VALUES(NULL, ?, ?, ?, ?, ?, NULL, ?, ?)");
            pstmt.setInt(1, taskId);
            pstmt.setString(2, plugin_name);
            pstmt.setString(3, "java");
            pstmt.setString(4, version_id);
            pstmt.setString(5, generate_report_string(stage, fields, sample, failed));
            pstmt.setString(7, sample);

            if (! failed && (fields[0].matches("benign") || fields[0].matches("malicious") || fields[0].matches("suspicious"))) {
                //submit benign or malicious or suspicious
                pstmt.setString(6, "done");
            } else {
                //error getting analysis results or failed before
                pstmt.setString(6, "error");
            }
            //pstmt.executeUpdate();
            pstmt.close();
        } catch (Exception e) {
            log.error("DB_ERROR " + e.toString());
        } finally {
            if (conn != null) {
                try {
                    conn.close();
                } catch (Exception e) {
                }
            }
        }
    }

    private boolean want_stage_2(String stage_1_result) {
        String[] fields = null;
	if (stage_1_result != null) {
		fields = stage_1_result.split(" ");
	} else {
		return true;
	}
	return fields[0].matches("benign");
    }

    private void run_stage(int stage, File dump, int taskId, String sample) throws IOException {
	int ret = 0;
	boolean interrupted;
	String stage_analyzer;
        ArrayList<String> results = new ArrayList<String>();
	log.debug("Starting stage " + stage +" analyzer");
	if (stage == 1) {
		stage_analyzer= "/opt/bin/appletanalysis.py";
	} else if (stage == 2) {
		stage_analyzer= "/opt/bin/jarhead.py";
	} else {
		log.error("No analyzer for stage " + stage + " found");
		return;
	}
        File result = File.createTempFile("appletplugin", ".result");
	final String cmdline = analyzer + " " + stage_analyzer + " "
	    + dump.getAbsolutePath() + " "
	    + result.getAbsolutePath();
	do {
	    interrupted = false;
	    try {
	        ret = Runtime.getRuntime().exec(cmdline).waitFor();
	        log.debug("Ran " + cmdline + " (exit: " + ret + ")");
	    } catch (InterruptedException e) {
	        interrupted = true;
	    }
	} while (interrupted);
	if (ret != 0) {
	    log.error("Error running the stage " + stage + " analyzer (cmdline was: " + cmdline + ")");
	    result.delete();
	    if (stage == 1) {
		run_stage(2, dump, taskId, sample);
	    } else {
		submit_result(stage, null, taskId, true, sample);
	    }
	    return;
	}
	BufferedReader br = new BufferedReader(new FileReader(result));
	try {
	    String line;
	    while ((line = br.readLine()) != null)  {
	        results.add(line);
	    }
	} finally {
	    br.close();
	}
	result.delete();
	if (results.size() == 0) {
	    log.error("Did not get results for stage " + stage);
	    if (stage == 1) {
		run_stage(2, dump, taskId, sample);
	    } else {
		submit_result(stage, null, taskId, true, sample);
	    }
	    return;
	}
	if (stage == 1 && want_stage_2(results.get(0))) {
		run_stage(2, dump, taskId, sample);
		return;
	} else {
		submit_result(stage, results.get(0), taskId, false, sample);
	}
    }

    /**
     * Analyze an applet.
     *
     * @param taskId The ID of the current analysis task
     * @param url The URL of the page containing the applet
     * @param appletCodeType The type of code: AppletPlugin.CLASS_CODE_TYPE or AppletPlugin.JAR_CODE_TYPE
     * @param appletCode The jar/class (depending on appletCodeType) containing the applet's code
     * @param appletClassName The applet's class name
     * @param width The applet's width (null if unspecified)
     * @param height The applet's height (null if unspecified)
     * @param params The params passed to the applet
     *
     * @throws IOException
     */
    public void analyze(int taskId, URL url, int appletCodeType, InputStream appletCode, String appletClassName, Integer width, Integer height, Hashtable<String,String> params) throws IOException {
        File dump;
        String sample = "";
        log.debug("Analyzing " + url + " (" + taskId + ")");
        if (appletCodeType == AppletPlugin.CLASS_CODE_TYPE) {
            dump = File.createTempFile("appletplugin", ".class");
        } else {
            assert((appletCodeType == AppletPlugin.JAR_CODE_TYPE));
            dump = File.createTempFile("appletplugin", ".jar");
        }
        OutputStream output = new FileOutputStream(dump);
        try {
            int cnt = 0;
            int data;
            while ((data = appletCode.read()) != -1) {
                output.write(data);
                cnt++;
            }
            if (cnt == 0) {
                throw new IOException("empty appletfile provided");
            }
        } finally {
            output.close();
        }
        FileInputStream fi = new FileInputStream(dump);
        try {
            sample = md5sum(fi);
        } finally {
            fi.close();
        }
	if (dump.length() > 3 * 1024 * 1024) { // applets bigger than 3MiB are not malicious
		submit_result(0, "benign", taskId, false, sample);
	} else {
		run_stage(1, dump, taskId, sample);
	}
	dump.delete();
    }
}
