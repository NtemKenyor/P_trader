<?php
// Include the database connection file
require $_SERVER['DOCUMENT_ROOT']."/alltrenders/env_variables/accessor/accessor_main.php";

// Prepare an array to hold the response
$response = array("status" => "", "msg" => "", "row" => null);

// Check if all necessary POST parameters are set
if (isset($_POST['pair']) && isset($_POST['price']) && isset($_POST['quantity']) && 
    isset($_POST['amount']) && isset($_POST['status']) && isset($_POST['conditioned']) && 
    isset($_POST['addon']) && isset($_POST['comment'])) {

    // Retrieve POST data and sanitize inputs
    $pair = htmlspecialchars($_POST['pair']);
    $price = floatval($_POST['price']);
    $quantity = floatval($_POST['quantity']);
    $amount = floatval($_POST['amount']);
    $status = intval($_POST['status']);
    $hashed_key = htmlspecialchars($_POST['hashed_key']);
    $order_placed = htmlspecialchars($_POST['order_placed']);
    $profit = floatval($_POST['profit']);
    $conditioned = intval($_POST['conditioned']);
    $addon = htmlspecialchars($_POST['addon']);
    $comment = htmlspecialchars($_POST['comment']);
    $datetime = date('Y-m-d H:i:s'); // Set current timestamp

    // Prepare the SQL statement
    $sql = "INSERT INTO trading (`pair`, `price`, `quantity`, `amount`, `status`, `hashed_key`, `order_placed`, `profit`, `conditioned`, `addon`, `comment`, `datetime`)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

    // Initialize prepared statement
    if ($stmt = $connect->prepare($sql)) {
        // Bind parameters
        $stmt->bind_param("sddddssdisss", $pair, $price, $quantity, $amount, $status, $hashed_key, $order_placed, $profit, $conditioned, $addon, $comment, $datetime);
        
        // Execute the statement
        if ($stmt->execute()) {
            // If insertion is successful, set the response status and message
            $response['status'] = "success";
            $response['msg'] = "Record inserted successfully.";

            // Retrieve the last inserted ID
            $last_id = $connect->insert_id;

            // Retrieve the newly inserted row
            $sql = "SELECT * FROM trading WHERE id = ?";
            if ($stmt_sel = $connect->prepare($sql)) {
                $stmt_sel->bind_param("i", $last_id);
                $stmt_sel->execute();
                $result = $stmt_sel->get_result();

                if ($result->num_rows > 0) {
                    $response['row'] = $result->fetch_assoc();
                }
                $stmt_sel->close();
            }
        } else {
            $response['status'] = "error";
            $response['msg'] = "Error inserting record: " . $stmt->error;
        }

        // Close the statement
        $stmt->close();
    } else {
        $response['status'] = "error";
        $response['msg'] = "Error preparing statement: " . $connect->error;
    }

} else {
    $response['status'] = "error";
    $response['msg'] = "All parameters must be provided.";
}

// Close the database connection
$connect->close();

// Return the response as JSON
header('Content-Type: application/json');
echo json_encode($response);
?>
