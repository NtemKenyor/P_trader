<?php

include "keys.php";

header('Content-Type: application/json');

$response = array("status" => false, "message" => "", "data" => "");

if(isset($_POST["email_key"]) and isset($_POST["data"])){
    $key = $_POST["email_key"];
    $data = $_POST["data"];
    $email = "kensntems@gmail.com";

    if($key == $the_mailer_key){
        $to = $email;
        $subject = "Data Report Process";
        
        $message = '
        <html>
        <head>
        <title> Roynek Tech reports </title>
        <link rel="stylesheet" href="roynek.com/stylesheets/mailer.css" />
        </head>
        <body style="font-family: \'Lato\', sans-serif;background-color:#00058A; color: #ffffff; font-size: 18px; text-align: center;">
    
        <h3><center> A1in1/Alltrenders </center></h3>
        <p> Welcome to the Roynek Data report Systems.
            <b>
                '.$data.'
            </b>
        </p>
        </body>
        </html>
        ';
        
        // Always set content-type when sending HTML email
        $headers = "MIME-Version: 1.0" . "\r\n";
        $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
        
        // More headers: verifier
        $headers .= 'From: <a1in1@roynek.com>' . "\r\n";
        
        if(mail($to, $subject, $message, $headers)) {
            $response["status"] = true;
            $response["message"] = "Email sent successfully.";
            $response["data"] = $data;
        } else {
            $response["message"] = "Failed to send email.";
        }
    } else {
        $response["message"] = "Invalid email key.";
    }
} else {
    $response["message"] = "Required fields are missing.";
}

echo json_encode($response);

?>
