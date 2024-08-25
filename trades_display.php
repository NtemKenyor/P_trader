<?php
// Include the database connection file
require $_SERVER['DOCUMENT_ROOT']."/alltrenders/env_variables/accessor/accessor_main.php";

// Prepare an array to hold the response
$response = array("status" => "", "msg" => "", "row" => array());

// Prepare the SQL statement to retrieve all data
$sql = "SELECT * FROM trading";

// Execute the query
if ($result = $connect->query($sql)) {
    if ($result->num_rows > 0) {
        // Fetch all rows as an associative array
        $response['row'] = $result->fetch_all(MYSQLI_ASSOC);
        $response['status'] = "success";
        $response['msg'] = "Data retrieved successfully.";
    } else {
        $response['status'] = "success";
        $response['msg'] = "No records found.";
    }
    // Free result set
    $result->free();
} else {
    $response['status'] = "error";
    $response['msg'] = "Error retrieving data: " . $connect->error;
}

// Close the database connection
$connect->close();

// Return the response as JSON
header('Content-Type: application/json');
echo json_encode($response);
?>
