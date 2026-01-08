using UnityEngine;
using UnityEngine.InputSystem;

public class CarController : MonoBehaviour
{
    private float horizontalInput;
    private float verticalInput;
    private float steerAngle;
    private bool isBreaking;

    public WheelCollider frontLeftWheelCollider;
    public WheelCollider frontRightWheelCollider;
    public WheelCollider rearLeftWheelCollider;
    public WheelCollider rearRightWheelCollider;
    public Transform frontLeftWheelTransform;
    public Transform frontRightWheelTransform;
    public Transform rearLeftWheelTransform;
    public Transform rearRightWheelTransform;

    public float maxSteeringAngle = 30f;
    public float motorForce = 50f;
    public float brakeForce = 0f;

    [Header("Input System (New)")]
    [Tooltip("Input Action (Vector2) cho chuyển động: X = ngang, Y = dọc")]
    public InputActionReference moveAction;

    [Tooltip("Input Action (Button/Axis) cho phanh")]
    public InputActionReference brakeAction;

    private void OnEnable()
    {
        if (moveAction != null)
            moveAction.action.Enable();
        if (brakeAction != null)
            brakeAction.action.Enable();
    }

    private void OnDisable()
    {
        if (moveAction != null)
            moveAction.action.Disable();
        if (brakeAction != null)
            brakeAction.action.Disable();
    }

    private void FixedUpdate()
    {
        ReadInput();
        HandleMotor();
        HandleSteering();
        UpdateWheels();
    }

    private void ReadInput()
    {
        // Đọc từ Input System mới
        Vector2 move = Vector2.zero;
        if (moveAction != null)
            move = moveAction.action.ReadValue<Vector2>();

        float brakeValue = 0f;
        if (brakeAction != null)
            brakeValue = brakeAction.action.ReadValue<float>();

        horizontalInput = move.x;
        verticalInput = move.y;
        isBreaking = brakeValue > 0.5f;
    }

    private void HandleSteering()
    {
        steerAngle = maxSteeringAngle * horizontalInput;
        frontLeftWheelCollider.steerAngle = steerAngle;
        frontRightWheelCollider.steerAngle = steerAngle;
    }

    private void HandleMotor()
    {
        frontLeftWheelCollider.motorTorque = verticalInput * motorForce;
        frontRightWheelCollider.motorTorque = verticalInput * motorForce;

        brakeForce = isBreaking ? 3000f : 0f;
        frontLeftWheelCollider.brakeTorque = brakeForce;
        frontRightWheelCollider.brakeTorque = brakeForce;
        rearLeftWheelCollider.brakeTorque = brakeForce;
        rearRightWheelCollider.brakeTorque = brakeForce;
    }

    private void UpdateWheels()
    {
        UpdateWheelPos(frontLeftWheelCollider, frontLeftWheelTransform);
        UpdateWheelPos(frontRightWheelCollider, frontRightWheelTransform);
        UpdateWheelPos(rearLeftWheelCollider, rearLeftWheelTransform);
        UpdateWheelPos(rearRightWheelCollider, rearRightWheelTransform);
    }

    private void UpdateWheelPos(WheelCollider wheelCollider, Transform trans)
    {
        Vector3 pos;
        Quaternion rot;
        wheelCollider.GetWorldPose(out pos, out rot);
        trans.rotation = rot;
        trans.position = pos;
    }

}